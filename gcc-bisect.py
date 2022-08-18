#!/usr/bin/env python3

# one needs the following packages:
# python3-filelock python3-GitPython
# python3-semantic_version python3-termcolor zstd

import argparse
import configparser
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import filelock

from git import Repo

from semantic_version import Version

from termcolor import colored

# configuration
script_dirname = os.path.abspath(os.path.dirname(__file__))

# WARNING: older commits include wide-int branch merged commits
# close to base of trunk and 4.9, there is then some libgfortran relink issue
last_revision = '58a41b43b5f02c67544569c508424efa4115ad9f'

description_color = 'blue'
title_color = 'cyan'

oldest_release = '4.8.0'
oldest_active_branch = 10

# Other locations should not by set up by a script consumer
lock_path = os.path.join(script_dirname, '.gcc_build_binary.lock')
lock = filelock.FileLock(lock_path)
log_file = '/home/marxin/Programming/script-misc/gcc-build.log'

patches_folder = os.path.join(script_dirname, 'gcc-bisect-patches')
patches = ['0001-Use-ucontext_t-not-struct-ucontext-in-linux-unwind.h.patch',
           'gnu-inline.patch', 'ubsan.patch', 'mallinfo.patch']

DESC = 'Bisect by prebuilt GCC binaries.'
parser = argparse.ArgumentParser(description=DESC)
parser.add_argument('command', nargs='?', metavar='command',
                    help='GCC command')
parser.add_argument('--silent', action='store_true',
                    help='Do not print stderr and stdout output')
parser.add_argument('-x', '--negate', action='store_true',
                    help='FAIL if result code is equal to zero')
parser.add_argument('-p', '--pull', action='store_true',
                    help='Pull repository')
parser.add_argument('-l', '--only-latest', action='store_true',
                    help='Test only latest revisions')
parser.add_argument('-s', '--bisect-start', help='Bisection start revision')
parser.add_argument('-e', '--bisect-end', help='Bisection end revision')
parser.add_argument('-i', '--ice', action='store_true',
                    help='Grep stderr for ICE')
parser.add_argument('-a', '--ask', action='store_true',
                    help='Ask about return code')
parser.add_argument('-o', '--old', action='store_true',
                    help='Test also old releases')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Verbose output')
parser.add_argument('--build', action='store_true', help='Build revisions')
parser.add_argument('--gc', action='store_true', help='GC unused revisions')
parser.add_argument('--print', action='store_true',
                    help='Print built revisions')
parser.add_argument('--success-exit-code', type=int, default=0,
                    help='Success exit code')
parser.add_argument('-u', '--unpack', help='Only unpack the revision and exit')
parser.add_argument('-t', '--timeout', type=float, help='Time out command')
parser.add_argument('--soft-timeout', type=float, help='Time out command (after it finishes)')

args = parser.parse_args()

config_location = str(Path.home().joinpath('.config/gcc-bisect.ini'))
config = configparser.ConfigParser()
config.read(config_location)

if 'Default' not in config:
    print('Cannot find Default section in config file: %s' % config_location)
    exit(127)

needed_variables = ['git_location', 'binaries_location', 'extract_location']
for nv in needed_variables:
    if nv not in config['Default']:
        print('Missing variable %s in config file: %s' % (nv, config_location))
        exit(127)

git_location = config['Default']['git_location']
binaries_location = config['Default']['binaries_location']
extract_location = config['Default']['extract_location']

repo = Repo(git_location)
head = repo.commit('origin/master')

build_times = []


def single_or_default(fn, items):
    return next(filter(fn, items), None)


def revisions_in_range(source, target):
    r = '%s..%s' % (source.hexsha, target.hexsha)
    return list(repo.iter_commits(r)) + [source]


def flush_print(text, end='\n'):
    print(text, end=end)
    sys.stdout.flush()


def strip_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def strip_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)]
    return text


def log(revision_hash, message):
    with open(log_file, 'a+') as f:
        f.write('%s:%s\n' % (revision_hash, message))


def build_failed_for_revision(revision_hash):
    if not os.path.exists(log_file):
        return False

    lines = [x.strip() for x in open(log_file).readlines()]
    for line in lines:
        i = line.find(':')
        revision = line[:i]
        if revision == revision_hash:
            return True

    return False


def run_cmd(command, strict=False):
    if isinstance(command, list):
        command = ' '.join(command)
    flush_print('Running: %s' % command)
    r = subprocess.run(command, shell=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if r.returncode == args.success_exit_code:
        return (True, None)
    else:
        flush_print('Command failed with return code %d' % r.returncode)
        try:
            lines = r.stderr.decode('utf-8').split('\n')
            error = ';'.join([x for x in lines if 'error: ' in x]).strip()
            if error != '':
                flush_print(error)
            assert not strict
        except UnicodeDecodeError as e:
            return (False, str(e))
        return (False, error)


class GitRevision:
    def __init__(self, commit):
        self.commit = commit
        self.has_binary = False

    def timestamp_str(self):
        return self.commit.committed_datetime.strftime('%d %b %Y %H:%M')

    def __str__(self):
        return self.commit.hexsha + ':' + self.timestamp_str()

    def short_hexsha(self):
        return self.commit.hexsha[0:16]

    def get_full_hash(self):
        cmd = 'git gcc-descr --full %s' % self.commit.hexsha
        r = subprocess.check_output(cmd, cwd=git_location, shell=True,
                                    encoding='utf8')
        parts = r.strip().split('-')
        assert len(parts) == 3
        parts[2] = parts[2][:17]
        return '-'.join(parts)

    def description(self, describe=False):
        hashtext = colored(self.short_hexsha(), description_color)
        if describe:
            hashtext = colored(self.get_full_hash(), 'green')
        return '%s(%s)(%s)' % (hashtext, self.timestamp_str(),
                               self.commit.author.email)

    def patch_name(self):
        return self.commit.hexsha + '.patch'

    def run(self, describe):
        with lock:
            self.decompress()
            start = datetime.now()

            my_env = os.environ.copy()
            my_env['PATH'] = (os.path.join(self.get_install_path(), 'bin')
                              + ':' + my_env['PATH'])
            ld_library_path = my_env['LD_LIBRARY_PATH'] if 'LD_LIBRARY_PATH' in my_env else ''
            my_env['LD_LIBRARY_PATH'] = os.path.join(self.get_install_path(), 'lib64') + ':' + ld_library_path

            try:
                r = subprocess.run(args.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=my_env, encoding='utf8', timeout=args.timeout)
                returncode = r.returncode
                stdout = r.stdout

            except subprocess.TimeoutExpired:
                returncode = 124
                stdout = ''
            finally:
                # handle ICE
                success = returncode == args.success_exit_code
                if success and args.ask:
                    if not args.silent:
                        flush_print(stdout, end='')
                    success = input('Retcode: ') == '0'
                elif args.ice:
                    messages = ['internal compiler error', 'Fatal Error', 'Internal compiler error',
                                'Please submit a full bug report', 'lto-wrapper: fatal error',
                                'Internal Error at ']
                    success = any(map(lambda m: m in stdout, messages))

                seconds = (datetime.now() - start).total_seconds()
                if args.soft_timeout and success:
                    success = seconds <= args.soft_timeout

                if args.negate:
                    success = not success

                text = colored('OK', 'green') if success else colored('FAILED', 'red') + ' (%d)' % returncode
                flush_print('  %s: [took: %3.2f s] result: %s' % (self.description(describe), seconds, text))
                if not args.silent:
                    flush_print(stdout, end='')

            return (success, stdout)

    def test(self, describe=False):
        if not self.has_binary:
            flush_print('  %s: missing binary' % (self.description()))
            return (False, None)
        else:
            return self.run(describe)

    def get_install_path(self):
        return os.path.join(extract_location, 'usr', 'local')

    def get_archive_path(self):
        return self.get_folder_path() + '.tar.zst'

    def get_folder_path(self):
        return os.path.join(binaries_location, self.commit.hexsha)

    def install(self, start):
        with lock:
            if os.path.exists(extract_location):
                shutil.rmtree(extract_location)
            run_cmd('make install DESTDIR=' + extract_location)
            with (open(os.path.join(extract_location, 'git-revision.txt'), 'w+')) as note:
                note.write(self.commit.hexsha)
            self.compress()
            took = datetime.now() - start
            build_times.append(took)
            flush_print('Build has taken: %s, avg: %s' % (str(took), str(sum(build_times,
                                                          timedelta(0)) / len(build_times))))
            log(self.commit.hexsha, 'OK')

    def build(self):
        build_command = 'nice make -j16 CFLAGS="-O2 -g0" CXXFLAGS="-O2 -g0"'
        if os.path.exists(self.get_archive_path()):
            if args.verbose:
                flush_print('Revision %s already exists' % (str(self)))
            return False
        elif build_failed_for_revision(self.commit.hexsha):
            if args.verbose:
                flush_print('Revision %s already failed' % (str(self)))
            return False
        else:
            flush_print('Building %s' % (str(self)))
            start = datetime.now()
            tmp_folder = '/dev/shm/gcc-bisect-tmp'

            if os.path.exists(tmp_folder):
                # try to reuse current build folder, should be very fast then
                repo.git.checkout(self.commit, force=True)

                os.chdir(git_location)
                # apply all patches
                for p in patches:
                    r = subprocess.run('patch -p1 < ' + os.path.join(patches_folder, p),
                                       shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8')
                    flush_print('applying patch %s with result: %d' % (p, r.returncode))

                os.chdir(tmp_folder)
                r = run_cmd(build_command)
                if r[0]:
                    self.install(start)
                    return True

            flush_print('Cannot build, clean-up and start again with clean build folder')
            if os.path.exists(tmp_folder):
                shutil.rmtree(tmp_folder)
            if not os.path.exists(tmp_folder):
                os.mkdir(tmp_folder)
            os.chdir(tmp_folder)
            cmd = [os.path.join(git_location, 'configure'), '--disable-bootstrap', '--enable-checking=yes',
                   '--disable-libsanitizer', '--enable-languages=c,c++,fortran',
                   '--without-isl', '--disable-cet',
                   '--disable-libstdcxx-pch', '--disable-static']
            run_cmd(cmd, True)
            run_cmd('echo "MAKEINFO = :" >> Makefile')
            r = run_cmd(build_command)
            if r[0]:
                self.install(start)
                return True
            else:
                log(self.commit.hexsha, r[1])
                flush_print('GCC build is not going to be installed')

            return False

    def strip(self):
        if os.path.exists(extract_location):
            run_cmd('find %s -exec strip --strip-debug {} \\;' % extract_location)

    def compress(self):
        archive = self.get_archive_path()
        self.strip()
        assert archive.endswith('.tar.zst')
        tarfile = archive.replace('.zst', '')
        current = os.getcwd()
        os.chdir(extract_location)
        subprocess.check_output('tar cfv %s *' % tarfile, shell=True)
        subprocess.check_output('zstd --rm -q -19 -T0 %s' % tarfile, shell=True)
        os.chdir(current)

    def decompress(self):
        archive = self.get_archive_path()
        if not os.path.exists(archive):
            return False

        shutil.rmtree(extract_location, ignore_errors=True)
        os.makedirs(extract_location)
        cmd = 'zstdcat -T0 %s | tar x -C %s' % (archive, extract_location)
        subprocess.check_output(cmd, shell=True)
        return True

    def print_status(self):
        status = colored('OK', 'green') if self.has_binary else colored('missing binary', 'yellow')
        flush_print('%s: %s' % (self.description(), status))


class Release(GitRevision):
    def __init__(self, name, commit):
        GitRevision.__init__(self, commit)
        self.name = name

        if '-base' in self.name:
            return
        version_name = name
        if len(version_name.split('.')) == 2:
            version_name += '.0'
        self.version = Version(version_name)

    def __str__(self):
        return self.commit.hexsha + ':' + self.name

    def description(self, describe=False):
        return '%s (%s)(%s)' % (colored(self.name, description_color), self.short_hexsha(), self.timestamp_str())

    def patch_name(self):
        return self.name + '.patch'


class Branch(GitRevision):
    def __init__(self, name, commit):
        GitRevision.__init__(self, commit)
        self.name = name

    def __str__(self):
        return self.commit.hexsha + ':' + self.name

    def description(self, describe=False):
        return '%s (%s)(%s)' % (colored(self.name, description_color), self.short_hexsha(), self.timestamp_str())

    def print_info(self):
        base = repo.merge_base(head, self.commit)[0]
        branch_commits = revisions_in_range(base, self.commit)
        head_commits = revisions_in_range(base, head)

        built = set(map(lambda x: x.commit.hexsha, filter(lambda x: x.has_binary, g.latest)))
        existing_head_commits = list(filter(lambda x: x.hexsha in built, head_commits))
        flush_print('%3s-branch: branch commits: %8d, head distance: %8d (have: %d)' % (self.name, len(branch_commits),
                    len(head_commits), len(existing_head_commits)))


class GitRepository:
    RELEASE_BRANCH_PREFIX = 'origin/releases/gcc-'

    def __init__(self):
        self.master_branch = None
        self.releases = []
        self.branches = []
        self.branch_bases = []
        self.latest = []

        if args.pull:
            attempts = 10
            for _ in range(attempts):
                r = self.pull()
                if r:
                    break
                else:
                    time.sleep(30)

        self.parse_releases()
        self.parse_branches()
        self.parse_latest_revisions()
        self.releases.append(Release(self.get_master_branch() + '.0', head))

        self.all = [self.releases, self.branch_bases, self.branches, self.latest]
        self.initialize_binaries()

    def pull(self):
        flush_print('Pulling origin repository')
        try:
            repo.remotes['origin'].fetch()
            return True
        except Exception as e:
            flush_print(str(e))
            return False

    def parse_releases(self):
        releases = list(filter(lambda x: 'releases/gcc-' in x.name and 'prerelease' not in x.name, repo.tags))
        for r in releases:
            version = strip_prefix(r.name, 'releases/gcc-')
            if version.count('.') == 2:
                self.releases.append(Release(version, repo.commit(r.name)))

        self.releases = sorted(filter(lambda x: x.version >= Version(oldest_release), self.releases),
                               key=lambda x: x.version)

    def get_master_branch(self):
        if not self.master_branch:
            self.master_branch = str(int(self.branches[-1].name) + 1)
        return self.master_branch

    def parse_branches(self):
        remote = repo.remotes['origin']
        # support bases for 5+ releases
        branches = list(filter(lambda x: self.RELEASE_BRANCH_PREFIX in x.name and '.' not in x.name, remote.refs))
        branches = sorted(branches, key=lambda x: int(strip_prefix(x.name, self.RELEASE_BRANCH_PREFIX)))
        for b in branches:
            name = strip_prefix(b.name, self.RELEASE_BRANCH_PREFIX)
            branch_commit = repo.commit(b.name)
            if name and int(name) >= oldest_active_branch:
                self.branches.append(Branch(name, branch_commit))
            base = repo.merge_base(head, branch_commit)[0]
            self.branch_bases.append(Release(name + '-base', base))
        self.branches.append(Branch(self.get_master_branch(), head))

    def parse_latest_revisions(self):
        for c in repo.iter_commits(last_revision + '..origin/master', first_parent=True):
            self.latest.append(GitRevision(c))

    @staticmethod
    def get_patch_name_tokens(file):
        r = os.path.splitext(os.path.basename(file))[0].split('..')
        return r

    def print_repo(self):
        flush_print(colored('Releases', title_color))
        for r in self.releases:
            r.print_status()

        flush_print(colored('\nActive branches', title_color))
        for r in self.branches:
            r.print_info()
            r.print_status()

        flush_print(colored('\nActive branch bases', title_color))
        for r in self.branch_bases:
            r.print_status()

        existing_revisions = len(list(filter(lambda x: x.has_binary, self.latest)))
        missing = len(self.latest) - existing_revisions
        flush_print(colored('\nLatest %d revisions (have: %d, missing: %d):'
                            % (len(self.latest), existing_revisions, missing), title_color))
        for r in self.latest:
            r.print_status()

    def build(self):
        for source in self.all:
            for r in source:
                r.build()

    def initialize_binaries(self):
        files = os.listdir(binaries_location)
        existing = set()
        for f in files:
            if f.endswith('.tar.zst'):
                existing.add(f.split('.')[0])

        for source in self.all:
            for r in source:
                if r.commit.hexsha in existing:
                    r.has_binary = True

    def find_commit(self, name, candidates):
        if 'base' in name:
            b = single_or_default(lambda x: x.name == name, self.branch_bases)
            if b:
                name = b.commit.hexsha
        elif '-' in name:
            # Support the GCC format: r11-3685-gfcae5121154d1c33
            name = name.split('-')[-1][1:]
        return single_or_default(lambda x: x.commit.hexsha.startswith(name), candidates)

    def bisect(self):
        if not args.old:
            self.releases = list(filter(lambda x: x.version.major >= oldest_active_branch, self.releases))

        self.failing_branches = None
        if not args.only_latest:
            flush_print(colored('Releases', title_color))
            self.failing_branches = []
            for r in self.releases:
                r.test()

            flush_print(colored('\nActive branches', title_color))
            for r in self.branches:
                report = not r.test()[0]
                if args.ice:
                    report = not report
                if report:
                    self.failing_branches.append(r.name)

            flush_print(colored('\nActive branch bases', title_color))
            for r in self.branch_bases:
                r.test()

        flush_print(colored('\nBisecting latest revisions', title_color))
        candidates = list(filter(lambda x: x.has_binary, self.latest))

        # test whether there's a change in return code

        if args.bisect_start:
            r = self.find_commit(args.bisect_start, candidates)
            candidates = candidates[candidates.index(r):]

        if args.bisect_end:
            r = self.find_commit(args.bisect_end, candidates)
            candidates = candidates[:candidates.index(r)+1]

        first = candidates[0].test()[0]
        last = candidates[-1].test()[0]

        if first != last:
            self.bisect_recursive(candidates, first, last)
        else:
            flush_print('  bisect finished: ' + colored('there is no change!', 'red'))

    def print_bugzilla_title(self, output, revision):
        for line in output.split('\n'):
            m = re.match('.*internal compiler error: (?P<details>.*)', line)
            if m:
                prefix = ''
                if self.failing_branches is not None:
                    if len(self.failing_branches) and len(self.failing_branches) != len(self.branches):
                        prefix = f'[{"/".join(self.failing_branches)} Regression] '
                summary = f'{prefix}ICE {m.group("details")} since {revision.get_full_hash()}'
                url = f'https://gcc.gnu.org/bugzilla/enter_bug.cgi?product=gcc&short_desc={quote(summary)}&' \
                      f'cc={revision.commit.author.email}'
                print(f'{colored("Bugzilla:", "yellow")} \u001b]8;;{url}\u001b\\{summary}\u001b]8;;\u001b\\')
                return

    def bisect_recursive(self, candidates, r1, r2):
        if len(candidates) == 2:
            flush_print(f'\nFirst change is ({candidates[0].short_hexsha()}):')
            output = candidates[0].test(describe=True)
            print(candidates[0].commit.message)
            candidates[1].test(describe=True)
            print(candidates[1].commit.message)
            revisions = revisions_in_range(candidates[1].commit, candidates[0].commit)
            length = len(revisions) - 2
            if length > 0:
                flush_print(colored('Revisions in between: %d' % length, 'red', attrs=['bold']))
            self.print_bugzilla_title(output[1], candidates[0])
        else:
            steps = math.ceil(math.log2(len(candidates))) - 1
            flush_print('  bisecting: %d revisions (~%d steps)' % (len(candidates), steps))
            assert r1 != r2
            index = int(len(candidates) / 2)
            middle = candidates[index].test()[0]
            if r1 == middle:
                self.bisect_recursive(candidates[index:], middle, r2)
            else:
                assert middle == r2
                self.bisect_recursive(candidates[:index+1], r1, middle)

    def gc(self):
        candidates = {r.commit.hexsha for r in self.latest + self.branches + self.releases}
        folders = {folder.split('.')[0] for folder in os.listdir(binaries_location)}
        todelete = folders - candidates
        print(f'Builds found: {len(candidates)}, can be removed: {len(todelete)}')
        if not todelete:
            return
        answer = input('Do you want to remove it (yes/no)?')
        if answer == 'yes':
            for file in todelete:
                path = Path(binaries_location, file + '.tar.zst')
                print(f'Removing {path}')
                path.unlink()


# MAIN
g = GitRepository()
if args.print:
    g.print_repo()
elif args.build:
    g.build()
elif args.unpack:
    try:
        commit = g.find_commit(args.unpack, g.latest + g.branches)
        with lock:
            commit.decompress()
            print(f'Revision extracted to: {commit.get_install_path() + "/bin"}')
    except Exception as e:
        print(f'Cannot find revision: {e}')
        exit(1)
elif args.gc:
    g.gc()
else:
    if not args.command:
        print('Missing command for bisection!')
        exit(1)
    else:
        g.bisect()
