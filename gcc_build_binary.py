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

from datetime import datetime
from termcolor import colored
from git import Repo

script_dirname = os.path.abspath(os.path.dirname(__file__))
last_revision_count = 3000
lock = filelock.FileLock('/tmp/gcc_build_binary.lock')
description_color = 'blue'

parser = argparse.ArgumentParser(description='Build GCC binaries.')
parser.add_argument('git_location', metavar = 'git', help = 'Location of git repository')
parser.add_argument('install', metavar = 'install', help = 'Installation location')
parser.add_argument('action', nargs = '?', metavar = 'action', help = 'Action', default = 'print', choices = ['print', 'build', 'bisect'])
parser.add_argument('command', nargs = '?', metavar = 'command', help = 'GCC command')
parser.add_argument('--verbose', action = 'store_true', help = 'Verbose logging')
parser.add_argument('--negate', action = 'store_true', help = 'FAIL if result code is equal to zero')
parser.add_argument('--bisect', action = 'store_true', help = 'Bisect releases')

args = parser.parse_args()

repo = Repo(args.git_location)
head = repo.commit('parent/master')

def strip_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def strip_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)]
    return text

def run_cmd(command, strict = False):
    if isinstance(command, list):
        command = ' '.join(command)
    print('Running: %s' % command)
    try:
        with open('/tmp/gcc-build.stderr', 'a') as err:
            subprocess.check_output(command, shell = True, stderr = err)
        return True
    except subprocess.CalledProcessError as e:
        print(str(e))
        lines = e.output.decode('utf-8').split('\n')
        print('\n'.join(lines))
        assert not strict
        return False

def revisions_in_range(source, target):
    r = '%s..%s' % (source.hexsha, target.hexsha)
    return list(repo.iter_commits(r))

class GitRevision:
    def __init__(self, commit):
        self.commit = commit
        self.has_binary = False

    def timestamp_str(self):
        return self.commit.committed_datetime.strftime('%d %b %Y %H:%M')

    def __str__(self):
        return self.commit.hexsha + ':' + self.timestamp_str()

    def description(self):
        return colored(self.commit.hexsha[0:16], description_color) + '(' + self.timestamp_str() + ')'

    def patch_name(self):
        return self.commit.hexsha + '.patch'

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

            success = r == 0
            if args.negate:
                success = not success

            text = colored('OK', 'green') if success else colored('FAILED', 'red')
            print('  %s: [took: %3.3fs] running command with result: %s' % (self.description(), (datetime.now() - start).total_seconds(), text))
            if args.verbose:
                print(open(log).read(), end = '')

            if clean:
                self.remove_extracted()

        return success

    def test(self):
        if not self.has_binary:
            print('  %s: missing binary' % (self.description()))
            return False
        else:
            return self.run()

    def get_binary_path(self):
        return os.path.join(self.get_folder_path(), 'bin/gcc')

    def get_archive_path(self):
        return os.path.join(self.get_folder_path(), 'archive.7z')

    def get_folder_path(self):
        return os.path.join(args.install, 'gcc-' + self.commit.hexsha)

    def apply_patch(self, revision):
        p = os.path.join(script_dirname, 'gcc-release-patches', self.patch_name())
        if os.path.exists(p):
            print('Existing patch: %s' % p)
            os.chdir(args.git_location)
            run_cmd('patch -p1 < %s' % p)

    def build(self, is_release, compress_binary):
        l = os.path.join(args.install, 'gcc-' + self.commit.hexsha)
        if os.path.exists(l):
            print('Revision %s already exists' % (str(self)))
        else:
            start = datetime.now()
            temp = tempfile.mkdtemp()
            repo.git.checkout(self.commit, force = True)
            self.apply_patch(self)
            print('Bulding %s' % (str(self)))
            os.chdir(temp)
            print('Bulding in %s' % temp)
            cmd = [os.path.join(args.git_location, 'configure'), '--prefix', l, '--disable-bootstrap', '--enable-checking=yes']
            if not is_release:
                cmd += ['--disable-libsanitizer', '--disable-multilib', '--enable-languages=c,c++,fortran']
            run_cmd(cmd, True)
            run_cmd('echo "MAKEINFO = :" >> Makefile')
            cmd = 'nice make -j10'
            # TODO: hack because of -j problem seen on 5.x releases
            if is_release and self.name.startswith('5.') and not self.name.startswith('5.4'):
                cmd = 'nice make'
            r = run_cmd(cmd)
            if r:
                run_cmd('make install')
                shutil.rmtree(temp)
                print('Build has taken: %s' % str(datetime.now() - start))

                if compress_binary:
                    self.compress()
            else:
                print('GCC build is not going to be installed')

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
        cmd = '7z x %s -o%s -aoa' % (archive, args.install)
        subprocess.check_output(cmd, shell = True)
        return True

    def print_status(self):
        status = colored('OK', 'green') if self.has_binary else colored('missing binary', 'yellow')
        print('%s: %s' % (self.description(), status))

class Release(GitRevision):
    def __init__(self, name, commit):
        GitRevision.__init__(self, commit)
        self.name = name

    def __str__(self):
        return self.commit.hexsha + ':' + self.name

    def description(self):
        return '%s (%s)' % (colored(self.name, description_color), self.commit.hexsha)

    def patch_name(self):
        return self.name + '.patch'

class Branch(GitRevision):
    def __init__(self, name, commit):
        GitRevision.__init__(self, commit)
        self.name = name

    def __str__(self):
        return self.commit.hexsha + ':' + self.name

    def description(self):
        return '%s (%s)' % (colored(self.name, description_color), self.commit.hexsha)

    def print_info(self):
        base = repo.merge_base(head, self.commit)[0]
        branch_commits = revisions_in_range(base, self.commit)
        head_commits = revisions_in_range(base, head)
        print('%3s-branch: branch commits: %8d, head distance: %8d' % (self.name, len(branch_commits), len(head_commits)))

class GitRepository:
    def __init__(self):
        self.releases = []
        self.branches = []
        self.branch_bases = []
        self.latest = []

        self.parse_releases()
        self.parse_branches()
        self.parse_latest_revisions()
        self.initialize_binaries()

    def parse_releases(self):
        releases = list(filter(lambda x: x.name.endswith('-release'), repo.tags))
        for r in releases:
            version = strip_suffix(strip_prefix(r.name, 'gcc-'), '-release').replace('_', '-').replace('-', '.')
            self.releases.append(Release(version, repo.commit(r.name)))

        # missing tag
        if not any(map(lambda x: x.name == '5.4.0', self.releases)):
            self.releases.append(Release('5.4.0', repo.commit('32c3b88e8ced4b6d022484a73c40f3d663e20fd4')))
        self.releases = sorted(filter(lambda x: x.name >= '4.5.0', self.releases), key = lambda x: x.name)    

    def parse_branches(self):
        remote = repo.remotes['parent']
        branches = list(filter(lambda x: 'parent/gcc-' in x.name, remote.refs))
        for b in branches:
            name = strip_suffix(strip_prefix(b.name, 'parent/gcc-'), '-branch').replace('_', '.')
            if name >= '4.9':
                b = Branch(name, repo.commit(b.name))
                self.branches.append(b)
                base = repo.merge_base(head, b.commit)[0]
                self.branch_bases.append(Release(name + '-base', base))

    def parse_latest_revisions(self):
        for c in repo.iter_commits('parent/master~' + str(last_revision_count) + '..parent/master'):
            self.latest.append(GitRevision(c))

    def print(self):
        print('Releases')
        for r in self.releases:
            r.print_status()

        print('\nActive branches')
        for r in self.branches:
            r.print_info()
            r.print_status()

        print('\nActive branch bases')
        for r in self.branch_bases:
            r.print_status()

        print('\nLatest %d revisions' % last_revision_count)
        for r in self.latest:
            r.print_status()

    def build(self):
        for r in self.releases:
            r.build(True, False)

        for r in self.branches:
            r.build(False, True)

        for r in self.branch_bases:
            r.build(False, False)

        for r in self.latest:
            r.build(False, True)

    def initialize_binaries(self):
        folders = os.listdir(args.install)
        existing = set()
        for f in folders:
            full = os.path.join(args.install, f, 'bin/gcc')
            h = strip_prefix(os.path.basename(f), 'gcc-')
            if os.path.exists(full) or os.path.exists(os.path.join(args.install, f, 'archive.7z')):
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
        print('Releases')
        for r in self.releases:
            r.test()

        print('\nActive branches')
        for r in self.branches:
            r.test()

        print('\nActive branch bases')
        for r in self.branch_bases:
            r.test()

        print('\nBisecting latest revisions')
        candidates = list(filter(lambda x: x.has_binary, self.latest))

        # test whether there's a change in return code
        first = candidates[0].test()
        last = candidates[-1].test()

        if first != last:
            GitRepository.bisect_recursive(candidates, first, last)
        else:
            print('  bisect finished: ' +  colored('there is no change!', 'red'))

    @staticmethod
    def bisect_recursive(candidates, r1, r2):
        if len(candidates) == 2:
            print('\nFirst change is:\n')
            candidates[0].test()
            candidates[1].test()
            revisions = revisions_in_range(candidates[1].commit, candidates[0].commit)
            l = len(revisions) - 1
            print('Candidates in between: %d' % l)
        else:
            steps = math.ceil(math.log2(len(candidates))) - 1
            print('  bisecting: %d revisions (~%d steps)' % (len(candidates), steps))
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
