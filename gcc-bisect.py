#!/usr/bin/env python3

# one needs the following packages:
# python3-filelock python3-GitPython python3-semantic_version python3-termcolor zstd

import sys
import hashlib
import argparse
import json
import os
import subprocess
import tempfile
import shutil
import time
import math
import filelock
import re
import configparser

from datetime import datetime,timedelta
from termcolor import colored
from git import Repo
from semantic_version import Version
from pathlib import Path

# configuration
script_dirname = os.path.abspath(os.path.dirname(__file__))

# WARNING: older commits include wide-int branch merged commits
# close to base of trunk and 4.9, there is then some libgfortran relink issue
last_revision = '58a41b43b5f02c67544569c508424efa4115ad9f'

description_color = 'blue'
title_color = 'cyan'

oldest_release = '4.8'
oldest_active_branch = 8

# Other locations should not by set up by a script consumer
lock = filelock.FileLock(os.path.join(script_dirname, '.gcc_build_binary.lock'))
log_file = '/home/marxin/Programming/script-misc/gcc-build.log'

patches_folder = os.path.join(script_dirname, 'gcc-bisect-patches')
patches = ['0001-Use-ucontext_t-not-struct-ucontext-in-linux-unwind.h.patch', 'gnu-inline.patch', 'ubsan.patch']

parser = argparse.ArgumentParser(description='Bisect by prebuilt GCC binaries.')
parser.add_argument('command', nargs = '?', metavar = 'command', help = 'GCC command')
parser.add_argument('-t', '--silent', action = 'store_true', help = 'Silent logging')
parser.add_argument('-x', '--negate', action = 'store_true', help = 'FAIL if result code is equal to zero')
parser.add_argument('-p', '--pull', action = 'store_true', help = 'Pull repository')
parser.add_argument('-l', '--only-latest', action = 'store_true', help = 'Test only latest revisions')
parser.add_argument('-s', '--bisect-start', help = 'Bisection start revision')
parser.add_argument('-e', '--bisect-end', help = 'Bisection end revision')
parser.add_argument('--all', action = 'store_true', help = 'Run all revisions in a range')
parser.add_argument('--smart-sequence', action = 'store_true', help = 'Run all revisions in a smart sequence')
parser.add_argument('-i', '--ice', action = 'store_true', help = 'Grep stderr for ICE')
parser.add_argument('-a', '--ask', action = 'store_true', help = 'Ask about return code')
parser.add_argument('-o', '--old', action = 'store_true', help = 'Test also old releases')
parser.add_argument('-v', '--verbose', action = 'store_true', help = 'Verbose output')
parser.add_argument('--build', action = 'store_true', help = 'Build revisions')
parser.add_argument('--print', action = 'store_true', help = 'Print built revisions')

args = parser.parse_args()

config_location = str(Path.home().joinpath('.config/gcc-bisect.ini'))
config = configparser.ConfigParser()
config.read(config_location)

if not 'Default' in config:
    print('Cannot find Default section in config file: %s' % config_location)
    exit(127)

needed_variables = ['git_location', 'binaries_location', 'extract_location']
for nv in needed_variables:
    if not nv in config['Default']:
        print('Missing variable %s in config file: %s' % (nv, config_location))
        exit(127)

git_location = config['Default']['git_location']
binaries_location = config['Default']['binaries_location']
extract_location = config['Default']['extract_location']

repo = Repo(git_location)
head = repo.commit('origin/master')

build_times = []

def single_or_default(fn, items):
    r = list(filter(fn, items))
    if len(r) == 1:
        return r[0]
    else:
        raise Exception()

def revisions_in_range(source, target):
    r = '%s..%s' % (source.hexsha, target.hexsha)
    return list(repo.iter_commits(r)) + [source]

def flush_print(text, end = '\n'):
    print(text, end = end)
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
    for l in lines:
        i = l.find(':')
        revision = l[:i]
        if revision == revision_hash:
            return True

    return False

def run_cmd(command, strict = False):
    if isinstance(command, list):
        command = ' '.join(command)
    flush_print('Running: %s' % command)
    r = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    if r.returncode == 0:
        return (True, None)
    else:
        flush_print('Command failed with return code %d' % r.returncode)
        lines = r.stderr.decode('utf-8').split('\n')
        error = ';'.join([x for x in lines if 'error: ' in x]).strip()
        if error != '':
            flush_print(error)
        assert not strict
        return (False, error)

def get_release_name(version):
    v = Version(version)
    if v.major < 5:
        return '%d.%d' % (v.major, v.minor)
    else:
        return v.major

def filter_versions(versions):
    seen = set()
    r = []
    versions = reversed(versions)
    for i, v in enumerate(versions):
        name = get_release_name(v)
        if not name in seen:
            seen.add(name)
            r.append(v)

    return reversed(r)

def generate_sequence(maximum):
    values = []
    todo = [(0, maximum - 1)]
    while len(todo) > 0:
        x = todo.pop(0)
        min = x[0]
        max = x[1]
        if not min in values:
            values.append(min)

        if not max in values:
            values.append(max)
        diff = max - min
        if diff > 1:
            half = min + int(diff / 2)
            todo.append((min, half))
            todo.append((half, max))

    # validate that
    assert len(values) == maximum
    return values

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

    def description(self, describe=False):
        hash = colored(self.short_hexsha(), description_color)
        if describe:
            r = subprocess.check_output('git gcc-descr --full %s' % self.commit.hexsha, cwd=git_location, shell=True, encoding='utf8')
            parts = r.strip().split('-')
            assert len(parts) == 3
            parts[2] = parts[2][:17]
            hash = colored('-'.join(parts), 'green')
        return '%s(%s)(%s)' % (hash, self.timestamp_str(), self.commit.author.email)

    def patch_name(self):
        return self.commit.hexsha + '.patch'

    def run(self, describe):
        start = datetime.now()
        log = '/tmp/output'
        with lock:
            if os.path.exists(self.get_archive_path()):
                self.decompress()

            my_env = os.environ.copy()
            my_env['PATH'] = os.path.join(self.get_install_path(), 'bin') + ':' + my_env['PATH']
            ld_library_path = my_env['LD_LIBRARY_PATH'] if 'LD_LIBRARY_PATH' in my_env else ''
            my_env['LD_LIBRARY_PATH'] = os.path.join(self.get_install_path(), 'lib64') + ':' + ld_library_path
            with open(log, 'w') as out:
                r = subprocess.call(args.command, shell = True, stdout = out, stderr = out, env = my_env)

            # handle ICE
            output = open(log).read()
            success = r == 0
            if success and args.ask:
                if not args.silent:
                    flush_print(output, end = '')
                success = input("Retcode: ") == '0'
            elif args.ice:
                messages = ['internal compiler error', 'Fatal Error', 'Internal compiler error', 'Please submit a full bug report',
                        'lto-wrapper: fatal error']
                success = any(map(lambda m: m in output, messages))

            if args.negate:
                success = not success

            text = colored('OK', 'green') if success else colored('FAILED', 'red') + ' (%d)' % r
            flush_print('  %s: [took: %3.3fs] result: %s' % (self.description(describe), (datetime.now() - start).total_seconds(), text))
            if not args.silent:
                flush_print(output, end = '')

        return success

    def test(self, describe = False):
        if not self.has_binary:
            flush_print('  %s: missing binary' % (self.description()))
            return False
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
            flush_print('Build has taken: %s, avg: %s' % (str(took), str(sum(build_times, timedelta(0)) / len(build_times))))
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
                repo.git.checkout(self.commit, force = True)

                os.chdir(git_location)
                # apply all patches
                for p in patches:
                    r = subprocess.run('patch -p1 < ' + os.path.join(patches_folder, p),
                            shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = 'utf8')
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
            run_cmd('find %s -exec strip --strip-debug {} \;' % extract_location)

    def compress(self):
        archive = self.get_archive_path()
        self.strip()
        assert archive.endswith('.tar.zst')
        tarfile = archive.replace('.zst', '')
        current = os.getcwd()
        os.chdir(extract_location)
        subprocess.check_output('tar cfv %s *' % tarfile, shell = True)
        subprocess.check_output('zstd --rm -q -19 -T0 %s' % tarfile, shell = True)
        os.chdir(current)

    def decompress(self):
        archive = self.get_archive_path()
        if not os.path.exists(archive):
            return False

        shutil.rmtree(extract_location, ignore_errors = True)
        os.makedirs(extract_location)
        cmd = 'zstdcat -T0 %s | tar x -C %s' % (archive, extract_location)
        subprocess.check_output(cmd, shell = True)
        return True

    def print_status(self):
        status = colored('OK', 'green') if self.has_binary else colored('missing binary', 'yellow')
        flush_print('%s: %s' % (self.description(), status))

class Release(GitRevision):
    def __init__(self, name, commit):
        GitRevision.__init__(self, commit)
        self.name = name

    def __str__(self):
        return self.commit.hexsha + ':' + self.name

    def description(self, describe=False):
        return '%s (%s)(%s)' % (colored(self.name, description_color), self.short_hexsha(), self.timestamp_str())

    def patch_name(self):
        return self.name + '.patch'

    @staticmethod
    def print_known_to(text, versions):
        print('known-to-%s: %s' % (text, ', '.join(versions)))

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
        flush_print('%3s-branch: branch commits: %8d, head distance: %8d (have: %d)' % (self.name, len(branch_commits), len(head_commits), len(existing_head_commits)))

class GitRepository:
    RELEASE_BRANCH_PREFIX = 'origin/releases/gcc-'

    def __init__(self):
        self.releases = []
        self.branches = []
        self.branch_bases = []
        self.latest = []

        if args.pull:
            attempts = 10
            for i in range(attempts):
                r = self.pull()
                if r:
                    break
                else:
                    time.sleep(30)

        self.parse_releases()
        self.parse_branches()
        self.parse_latest_revisions()

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
        releases = list(filter(lambda x: 'releases/gcc-' in x.name and not 'prerelease' in x.name, repo.tags))
        for r in releases:
            version = strip_prefix(r.name, 'releases/gcc-')
            self.releases.append(Release(version, repo.commit(r.name)))

        self.releases = sorted(filter(lambda x: x.name >= oldest_release, self.releases), key = lambda x: x.name)

    def parse_branches(self):
        remote = repo.remotes['origin']
        # support bases for 5+ releases
        branches = list(filter(lambda x: self.RELEASE_BRANCH_PREFIX in x.name and '.' not in x.name, remote.refs))
        branches = sorted(branches, key = lambda x: int(strip_prefix(x.name, self.RELEASE_BRANCH_PREFIX)))
        for b in branches:
            name = strip_prefix(b.name, self.RELEASE_BRANCH_PREFIX)
            branch_commit = repo.commit(b.name)
            if name and int(name) >= oldest_active_branch:
                self.branches.append(Branch(name, branch_commit))
            base = repo.merge_base(head, branch_commit)[0]
            self.branch_bases.append(Release(name + '-base', base))

    def parse_latest_revisions(self):
        for c in repo.iter_commits(last_revision + '..origin/master', first_parent = True):
            self.latest.append(GitRevision(c))

    @staticmethod
    def get_patch_name_tokens(file):
        r = os.path.splitext(os.path.basename(file))[0].split('..')
        return r

    def print(self):
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
        flush_print(colored('\nLatest %d revisions (have: %d, missing: %d):' % (len(self.latest), existing_revisions, missing), title_color))
        for r in self.latest:
            r.print_status()

    def build(self):
        for l in self.all:
            for r in l:
                r.build()

    def initialize_binaries(self):
        files = os.listdir(binaries_location)
        existing = set()
        for f in files:
            if f.endswith('.tar.zst'):
                existing.add(f.split('.')[0])

        for l in self.all:
            for r in l:
                if r.commit.hexsha in existing:
                    r.has_binary = True

    def find_commit(self, name, candidates):
        if 'base' in name:
            b = single_or_default(lambda x: x.name == name, self.branch_bases)
            if b != None:
                name = b.commit.hexsha
        return single_or_default (lambda x: x.commit.hexsha.startswith(name), candidates)

    def bisect(self):
        if not args.old:
            self.releases = list(filter(lambda x: Version(x.name).major >= oldest_active_branch, self.releases))

        if not args.only_latest:
            flush_print(colored('Releases', title_color))
            results = {True: [], False: []}
            for r in self.releases:
                results[r.test()].append(r.name)

            Release.print_known_to('work', filter_versions(results[True]))
            Release.print_known_to('fail', filter_versions(results[False]))

            flush_print(colored('\nActive branches', title_color))
            for r in self.branches:
                r.test()

            flush_print(colored('\nActive branch bases', title_color))
            for r in self.branch_bases:
                r.test()

        flush_print(colored('\nBisecting latest revisions', title_color))
        candidates = list(filter(lambda x: x.has_binary, self.latest))

        # test whether there's a change in return code

        if args.bisect_start != None:
            r = self.find_commit(args.bisect_start, candidates)
            candidates = candidates[candidates.index(r):]

        if args.bisect_end != None:
            r = self.find_commit(args.bisect_end, candidates)
            candidates = candidates[:candidates.index(r)+1]

        if args.all:
            flush_print('  running: %d revisions' % len(candidates))
            for c in candidates:
                c.test()
        elif args.smart_sequence:
            flush_print('  running: %d revisions' % len(candidates))
            sequence = generate_sequence(len(candidates))
            for i in sequence:
                candidates[i].test()
        else:
            first = candidates[0].test()
            last = candidates[-1].test()

            if first != last:
                GitRepository.bisect_recursive(candidates, first, last)
            else:
                flush_print('  bisect finished: ' +  colored('there is no change!', 'red'))

    @staticmethod
    def bisect_recursive(candidates, r1, r2):
        if len(candidates) == 2:
            flush_print('\nFirst change is:')
            candidates[0].test(describe=True)
            print(candidates[0].commit.message)
            candidates[1].test(describe=True)
            print(candidates[1].commit.message)
            revisions = revisions_in_range(candidates[1].commit, candidates[0].commit)
            l = len(revisions) - 2
            if l > 0:
                flush_print(colored('Revisions in between: %d' % l, 'red', attrs = ['bold']))
        else:
            steps = math.ceil(math.log2(len(candidates))) - 1
            flush_print('  bisecting: %d revisions (~%d steps)' % (len(candidates), steps))
            assert r1 != r2
            index = int(len(candidates) / 2)
            middle = candidates[index].test()
            if r1 == middle:
                GitRepository.bisect_recursive(candidates[index:], middle, r2)
            else:
                assert middle == r2
                GitRepository.bisect_recursive(candidates[:index+1], r1, middle)

# MAIN
g = GitRepository()
if args.print:
    g.print()
elif args.build:
    g.build()
else:
    g.bisect()
