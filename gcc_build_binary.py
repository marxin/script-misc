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

from datetime import datetime
from termcolor import colored

script_dirname = os.path.abspath(os.path.dirname(__file__))
compress_older_than = 5
last_revision_count = 30

parser = argparse.ArgumentParser(description='Build GCC binaries.')
parser.add_argument('git_location', metavar = 'git', help = 'Location of git repository')
parser.add_argument('install', metavar = 'install', help = 'Installation location')
parser.add_argument('action', nargs = '?', metavar = 'action', help = 'Action', default = 'print', choices = ['print', 'build', 'test', 'gc', 'bisect'])
parser.add_argument('command', nargs = '?', metavar = 'command', help = 'GCC command')
parser.add_argument('--verbose', action = 'store_true', help = 'Verbose logging')
parser.add_argument('--negate', action = 'store_true', help = 'FAIL if result code is equal to zero')
parser.add_argument('--bisect', action = 'store_true', help = 'Bisect releases')

args = parser.parse_args()

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

class GitRevision:
    def __init__(self, git_line):
        tokens = git_line.split(';')
        self.hash = tokens[0]
        self.author = tokens[1]
        self.timestamp = datetime.fromtimestamp(int(tokens[2]))
        self.message = tokens[3]
        self.has_binary = False

    def timestamp_str(self):
        return self.timestamp.strftime('%d %b %Y %H:%M')

    def __str__(self):
        return self.hash + ':' + self.timestamp_str()

    def description(self):
        return self.hash[0:16] + '(' + self.timestamp_str() + ')'

    def patch_name(self):
        return self.hash + '.patch'

    def run(self):
        start = datetime.now()
        log = '/tmp/output'
        clean = False
        if not os.path.exists(self.get_binary_path()):
            clean = self.decompress()

        binary = strip_suffix(self.get_binary_path(), '/gcc')
        cmd = binary + '/' + args.command
        with open(log, 'w') as out:
            r = subprocess.call(cmd, shell = True, stdout = out, stderr = out)

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
        return os.path.join(args.install, 'gcc-' + self.hash)

    def apply_patch(self, revision):
        p = os.path.join(script_dirname, 'gcc-release-patches', self.patch_name())
        if os.path.exists(p):
            print('Existing patch: %s' % p)
            run_cmd('patch -p1 < %s' % p)

    def build(self, is_release):
        l = os.path.join(args.install, 'gcc-' + self.hash)
        if os.path.exists(l):
            print('Revision %s already exists' % (str(self)))
        else:
            start = datetime.now()
            temp = tempfile.mkdtemp()
            os.chdir(args.git_location)
            run_cmd('git checkout --force ' + self.hash)
            self.apply_patch(self)
            print('Bulding %s' % (str(self)))
            os.chdir(temp)
            print('Bulding in %s' % temp)
            cmd = [os.path.join(args.git_location, 'configure'), '--prefix', l, '--disable-bootstrap']
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

    def strip(self):
        if os.path.exists(self.get_binary_path()):
            run_cmd('find %s -exec strip --strip-debug {} \;' % self.get_folder_path())

    def compress(self):
        r = False
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
        print('%s: %s' % (str(self), status))

    @staticmethod
    def get_git_lines(start, end):
        cmd = 'git log --pretty=format:"%H;%an;%at;%s" ' + start + '..' + end
        lines = subprocess.check_output(cmd, shell = True).decode('utf-8').split('\n')
        return lines

class Release(GitRevision):
    def __init__(self, name, hash):
        GitRevision.__init__(self, GitRevision.get_git_lines(hash + '~', hash)[0])
        self.name = name
        self.hash = hash

    def __str__(self):
        return self.hash + ':' + self.name

    def description(self):
        return self.name

    def patch_name(self):
        return self.name + '.patch'

class GitRepository:
    def __init__(self):
        self.releases = []
        self.latest = []
        os.chdir(args.git_location)
        self.parse_releases()
        self.parse_latest_revisions()
        self.initialize_binaries()

    def parse_releases(self):
        r = subprocess.check_output('git show-ref --tags', shell = True)
        lines = r.decode('utf-8')
        for l in lines.split('\n'):
            l = l.strip()
            if l == '':
                continue

            tokens = l.split(' ')
            hash = tokens[0]
            name = tokens[1].split('/')[-1].replace('_', '-')
            if not name.startswith('gcc-') or not name.endswith('-release'):
                continue
            version = strip_suffix(strip_prefix(name, 'gcc-'), '-release').replace('-', '.')

            if not any(map(lambda x: x.name == version, self.releases)):
                self.releases.append(Release(version, hash))

        # missing tag
        if not any(map(lambda x: x.name == '5.4.0', self.releases)):
            self.releases.append(Release('5.4.0', '32c3b88e8ced4b6d022484a73c40f3d663e20fd4'))
        self.releases = sorted(filter(lambda x: x.name >= '4.5.0', self.releases), key = lambda x: x.name)    

    def parse_latest_revisions(self):
        for l in GitRevision.get_git_lines('parent/master~' + str(last_revision_count), 'parent/master'):
            self.latest.append(GitRevision(l.strip()))

    def print(self):
        print('Releases')
        for r in self.releases:
            r.print_status()

        print('\nLatest revisions')
        for r in self.latest:
            r.print_status()

    def compress_old(self):
        for r in self.latest[compress_older_than:]:
            if r.has_binary:
                if r.compress():
                    print(str(r) + ' has been compressed')

    def build(self):
        for r in self.latest:
            r.build(False)

        for r in self.releases:
            r.build(True)

    def initialize_binaries(self):
        folders = os.listdir(args.install)
        existing = set()
        for f in folders:
            full = os.path.join(args.install, f, 'bin/gcc')
            h = strip_prefix(os.path.basename(f), 'gcc-')
            if os.path.exists(full) or os.path.exists(os.path.join(args.install, f, 'archive.7z')):
                existing.add(h)

        for r in self.releases:
            if r.hash in existing:
                r.has_binary = True

        for r in self.latest:
            if r.hash in existing:
                r.has_binary = True

    def test(self):
        print('Releases')
        for r in self.releases:
            r.test()

        print('\nLatest revisions')
        for r in self.latest:
            r.test()

    def bisect(self):
        print('Releases')
        for r in self.releases:
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
elif args.action == 'test':
    g.test()
elif args.action == 'bisect':
    g.bisect()
elif args.action == 'gc':
    g.compress_old()
