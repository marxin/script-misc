#!/usr/bin/env python3

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

from datetime import datetime
from termcolor import colored
from git import Repo
from semantic_version import Version

# configuration
script_dirname = os.path.abspath(os.path.dirname(__file__))
patches_folder = os.path.join(script_dirname, 'gcc-release-patches')

last_revision_count = 11000
oldest_release = '4.5'
lock = filelock.FileLock('/tmp/gcc_build_binary.lock')
description_color = 'blue'
git_location = '/home/marxin/BIG/Programming/gcc/'
install_location = '/home/marxin/DATA/gcc-binaries/'
log_file = '/home/marxin/Programming/script-misc/gcc-build.log'

parser = argparse.ArgumentParser(description='Build GCC binaries.')
parser.add_argument('action', nargs = '?', metavar = 'action', help = 'Action', default = 'print', choices = ['print', 'build', 'bisect'])
parser.add_argument('command', nargs = '?', metavar = 'command', help = 'GCC command')
parser.add_argument('-s', '--silent', action = 'store_true', help = 'Silent logging')
parser.add_argument('-x', '--negate', action = 'store_true', help = 'FAIL if result code is equal to zero')
parser.add_argument('-p', '--pull', action = 'store_true', help = 'Pull repository')
parser.add_argument('--only-latest', action = 'store_true', help = 'Test only latest revisions')
parser.add_argument('--bisect-start', help = 'Bisection start revision')
parser.add_argument('--bisect-end', help = 'Bisection end revision')
parser.add_argument('-n', help = 'Number of revisions to build')
parser.add_argument('-i', '--ice', action = 'store_true', help = 'Grep stderr for ICE')

args = parser.parse_args()

to_build = 10**10 if args.n == None else int(args.n)

repo = Repo(git_location)
head = repo.commit('parent/master')

def revisions_in_range(source, target):
    r = '%s..%s' % (source.hexsha, target.hexsha)
    return list(repo.iter_commits(r))

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

    def description(self):
        return colored(self.short_hexsha(), description_color) + '(' + self.timestamp_str() + ')'

    def patch_name(self):
        return self.commit.hexsha + '.patch'

    def print_svn_revision(self):
        r = '.*svn/gcc/trunk@([0-9]+).*'
        for l in self.commit.message.split('\n'):
            m = re.match(r, l)
            if m != None:
                print('SVN revision: ' + m.group(1))
        print('Author: %s' % self.commit.author)

    def run(self):
        start = datetime.now()
        log = '/tmp/output'
        clean = False
        with lock:
            if os.path.exists(self.get_archive_path()):
                clean = self.decompress()

            my_env = os.environ.copy()
            my_env['PATH'] = os.path.join(self.get_folder_path(), 'bin') + ':' + my_env['PATH']
            my_env['LD_LIBRARY_PATH'] = os.path.join(self.get_folder_path(), 'lib64') + ':' + my_env['LD_LIBRARY_PATH']
            with open(log, 'w') as out:
                r = subprocess.call(args.command, shell = True, stdout = out, stderr = out, env = my_env)

            # handle ICE
            output = open(log).read()
            success = r == 0
            if args.ice:
                messages = ['internal compiler error', 'Fatal Error']
                success = any(map(lambda m: m in output, messages))

            if args.negate:
                success = not success

            text = colored('OK', 'green') if success else colored('FAILED', 'red')
            flush_print('  %s: [took: %3.3fs] result: %s' % (self.description(), (datetime.now() - start).total_seconds(), text))
            if not args.silent:
                flush_print(output, end = '')

            if clean:
                self.remove_extracted()

        return success

    def test(self):
        if not self.has_binary:
            flush_print('  %s: missing binary' % (self.description()))
            return False
        else:
            return self.run()

    def get_binary_path(self):
        return os.path.join(self.get_folder_path(), 'bin/gcc')

    def get_archive_path(self):
        return os.path.join(self.get_folder_path(), 'archive.7z')

    def get_folder_path(self):
        return os.path.join(install_location, 'gcc-' + self.commit.hexsha)

    def apply_patch(self, revision):
        p = os.path.join(patches_folder, self.patch_name())
        if not os.path.exists(p) and self.commit.hexsha in g.patches_map:
            p = os.path.join(patches_folder, g.patches_map[self.commit.hexsha])
        if os.path.exists(p):
            flush_print('Existing patch: %s' % p)
            os.chdir(git_location)
            run_cmd('patch -p1 -f < %s' % p)

    def build_with_limit(self, is_release, compress_binary):
        global to_build
        if to_build > 0:
            result = self.build(is_release, compress_binary)
            if result:
                to_build -= 1

    def build(self, is_release, compress_binary):
        l = os.path.join(install_location, 'gcc-' + self.commit.hexsha)
        if os.path.exists(l):
            flush_print('Revision %s already exists' % (str(self)))
            return False
        elif build_failed_for_revision(self.commit.hexsha):
            flush_print('Revision %s already failed' % (str(self)))
            return False
        else:
            tmp_folder = '/dev/shm/gcc-tmp'
            if os.path.exists(tmp_folder):
                shutil.rmtree(tmp_folder)
            start = datetime.now()
            if not os.path.exists(tmp_folder):
                os.mkdir(tmp_folder)
            temp = tempfile.mkdtemp(dir = tmp_folder)
            repo.git.checkout(self.commit, force = True)
            self.apply_patch(self)
            flush_print('Bulding %s' % (str(self)))
            os.chdir(temp)
            flush_print('Bulding in %s' % temp)
            cmd = [os.path.join(git_location, 'configure'), '--prefix', l, '--disable-bootstrap', '--enable-checking=yes']
            if not is_release:
                cmd += ['--disable-libsanitizer', '--disable-multilib', '--enable-languages=c,c++,fortran']
            run_cmd(cmd, True)
            run_cmd('echo "MAKEINFO = :" >> Makefile')
            cmd = 'nice make -j10'
            # TODO: hack because of -j problem seen on 5.x releases
            if is_release and self.name.startswith('5.') and not self.name.startswith('5.4'):
                cmd = 'nice make'
            r = run_cmd(cmd)
            result = True
            if r[0]:
                run_cmd('make install')
                flush_print('Build has taken: %s' % str(datetime.now() - start))
                log(self.commit.hexsha, 'OK')

                if compress_binary:
                    self.compress()
            else:
                log(self.commit.hexsha, r[1])
                flush_print('GCC build is not going to be installed')
                result = False

            shutil.rmtree(temp, ignore_errors = True)
            return result

    def strip(self):
        if os.path.exists(self.get_binary_path()):
            run_cmd('find %s -exec strip --strip-debug {} \;' % self.get_folder_path())

    def compress(self):
        r = False
        with lock:
            archive = self.get_archive_path()
            if not os.path.exists(archive):
                self.strip()
                subprocess.check_output('7z a %s %s' % (archive, self.get_folder_path()), shell = True)
                r = True

            self.remove_extracted()
        return r

    def remove_extracted(self):
        f = self.get_folder_path()
        for file in os.listdir(f):
            full = os.path.join(f, file)
            if os.path.isdir(full):
                shutil.rmtree(full)

    def decompress(self):
        archive = self.get_archive_path()
        if not os.path.exists(archive):
            return False
        cmd = '7z x %s -o%s -aoa' % (archive, install_location)
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

    def description(self):
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

    def description(self):
        return '%s (%s)(%s)' % (colored(self.name, description_color), self.short_hexsha(), self.timestamp_str())

    def print_info(self):
        base = repo.merge_base(head, self.commit)[0]
        branch_commits = revisions_in_range(base, self.commit)
        head_commits = revisions_in_range(base, head)

        built = set(map(lambda x: x.commit.hexsha, filter(lambda x: x.has_binary, g.latest)))
        existing_head_commits = list(filter(lambda x: x.hexsha in built, head_commits))
        flush_print('%3s-branch: branch commits: %8d, head distance: %8d (have: %d)' % (self.name, len(branch_commits), len(head_commits), len(existing_head_commits)))

class GitRepository:
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
                    sleep(30)

        self.parse_releases()
        self.parse_branches()
        self.parse_latest_revisions()
        self.initialize_binaries()
        self.parse_patches_range()

    def pull(self):
        flush_print('Pulling parent repository')
        try:
            repo.remotes['parent'].fetch()
            return True
        except Error as e:
            flush_print(str(e))
            return False

    def parse_releases(self):
        releases = list(filter(lambda x: x.name.endswith('-release'), repo.tags))
        for r in releases:
            version = strip_suffix(strip_prefix(r.name, 'gcc-'), '-release').replace('_', '-').replace('-', '.')
            self.releases.append(Release(version, repo.commit(r.name)))

        self.releases = sorted(filter(lambda x: x.name >= oldest_release, self.releases), key = lambda x: x.name)

    def parse_branches(self):
        remote = repo.remotes['parent']
        branches = list(filter(lambda x: 'parent/gcc-' in x.name, remote.refs))
        for b in branches:
            name = strip_suffix(strip_prefix(b.name, 'parent/gcc-'), '-branch').replace('_', '.')
            branch_commit = repo.commit(b.name)
            if name >= '5':
                b = Branch(name, branch_commit)
                self.branches.append(b)
            if name >= oldest_release:
                base = repo.merge_base(head, branch_commit)[0]
                self.branch_bases.append(Release(name + '-base', base))

    def parse_latest_revisions(self):
        for c in repo.iter_commits('parent/master~' + str(last_revision_count) + '..parent/master'):
            self.latest.append(GitRevision(c))

    def parse_patches_range(self):
        self.patches_map = {}
        for file in os.listdir(patches_folder):
            if '..' in file:
                tokens = os.path.splitext(file)[0].split('..')
                for r in revisions_in_range(repo.commit(tokens[0]), repo.commit(tokens[1])):
                    self.patches_map[r.hexsha] = file

    def print(self):
        flush_print('Releases')
        for r in self.releases:
            r.print_status()

        flush_print('\nActive branches')
        for r in self.branches:
            r.print_info()
            r.print_status()

        flush_print('\nActive branch bases')
        for r in self.branch_bases:
            r.print_status()

        flush_print('\nLatest %d revisions' % last_revision_count)
        for r in self.latest:
            r.print_status()

    def build(self):
        for r in self.releases:
            r.build_with_limit(True, False)

        for r in self.branch_bases:
            r.build_with_limit(False, False)

        for r in self.branches:
            r.build_with_limit(False, True)

        for r in self.latest:
            r.build_with_limit(False, True)

    def initialize_binaries(self):
        folders = os.listdir(install_location)
        existing = set()
        for f in folders:
            full = os.path.join(install_location, f, 'bin/gcc')
            h = strip_prefix(os.path.basename(f), 'gcc-')
            if os.path.exists(full) or os.path.exists(os.path.join(install_location, f, 'archive.7z')):
                existing.add(h)

        for r in self.releases:
            if r.commit.hexsha in existing:
                r.has_binary = True

        for r in self.branches:
            if r.commit.hexsha in existing:
                r.has_binary = True

        for r in self.branch_bases:
            if r.commit.hexsha in existing:
                r.has_binary = True

        for r in self.latest:
            if r.commit.hexsha in existing:
                r.has_binary = True

    def bisect(self):
        if not args.only_latest:
            flush_print('Releases')
            results = {True: [], False: []}
            for r in self.releases:
                results[r.test()].append(r.name)

            Release.print_known_to('work', filter_versions(results[True]))
            Release.print_known_to('fail', filter_versions(results[False]))

            flush_print('\nActive branches')
            for r in self.branches:
                r.test()

            flush_print('\nActive branch bases')
            for r in self.branch_bases:
                r.test()

        flush_print('\nBisecting latest revisions')
        candidates = list(filter(lambda x: x.has_binary, self.latest))

        # test whether there's a change in return code

        if args.bisect_start != None:
            r = list(filter(lambda x: x.commit.hexsha == args.bisect_start, candidates))[0]
            candidates = candidates[candidates.index(r):]

        if args.bisect_end != None:
            r = list(filter(lambda x: x.commit.hexsha == args.bisect_end, candidates))[0]
            candidates = candidates[:candidates.index(r)]

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
            candidates[0].test()
            candidates[0].print_svn_revision()
            print(candidates[0].commit.message)
            candidates[1].test()
            candidates[1].print_svn_revision()
            print(candidates[1].commit.message)
            revisions = revisions_in_range(candidates[1].commit, candidates[0].commit)
            l = len(revisions) - 1
            flush_print('Candidates in between: %d' % l)
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
if args.action == 'print':
    g.print()
elif args.action == 'build':
    g.build()
elif args.action == 'bisect':
    g.bisect()
