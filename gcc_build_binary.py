#!/usr/bin/env python3

import sys
import hashlib
import argparse
import json
import os
import subprocess
import tempfile
import shutil
import datetime
import time

from termcolor import colored

script_dirname = os.path.abspath(os.path.dirname(__file__))

def strip_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def strip_suffix(text, suffix):
    if text.endswith(suffix):
        return text[:-len(suffix)]
    return text

class GitRevision:
    def __init__(self, git_line):
        tokens = git_line.split(';')
        self.hash = tokens[0]
        self.author = tokens[1]
        self.timestamp = datetime.datetime.fromtimestamp(int(tokens[2]))
        self.message = tokens[3]
        self.has_binary = False

    def timestamp_str(self):
        return self.timestamp.strftime('%d %b %Y %H:%M')

    def __str__(self):
        return self.hash + ':' + self.timestamp_str()

    def description(self):
        return self.hash[0:16] + '(' + self.timestamp_str() + ')'

    def run(self, install, command, verbose, negate):
        log = '/tmp/output'
        binary = os.path.join(install, 'gcc-' + self.hash, 'bin')
        cmd = binary + '/' + command
        with open(log, 'w') as out:
            r = subprocess.call(cmd, shell = True, stdout = out, stderr = out)

        success = r == 0
        if negate:
            success = not success

        text = colored('OK', 'green') if success else colored('FAILED', 'red')
        print('  %s: running command with result: %s' % (self.description(), text))
        if verbose:
            print(open(log).read(), end = '')

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

    def test(self, install, command, verbose, negate):
        if not self.has_binary:
            print('  %s: missing binary' % (self.name))
        else:
            self.run(install, command, verbose, negate)

    def __str__(self):
        return self.hash + ':' + self.name

    def description(self):
        return self.name

class GitRepository:
    def __init__(self, location, install):
        self.location = location
        self.install = install

        self.releases = []
        self.latest = []
        os.chdir(location)
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

    def parse_latest_revisions(self, n = 1000):
        for l in GitRevision.get_git_lines('parent/master~' + str(n), 'parent/master'):
            self.latest.append(GitRevision(l.strip()))

    def print(self):
        print('Releases')
        for r in self.releases:
            print(str(r))

        print('\nLatest revisions')
        for r in self.latest:
            if r.has_binary:
                print(str(r))

    def apply_patch(self, revision):
        p = os.path.join(script_dirname, 'gcc-release-patches', revision.name + '.patch')
        if os.path.exists(p):
            print('Existing patch: %s' % p)
            self.run_cmd('patch -p1 < %s' % p)

    def build_release(self, release, install):
        l = os.path.join(install, 'gcc-' + release.hash)
        if os.path.exists(l):
            print('Release %s already exists' % (str(release)))
        else:
            temp = tempfile.mkdtemp()
            os.chdir(self.location)
            self.run_cmd('git checkout --force ' + release.hash)
            self.apply_patch(release)
            print('Bulding %s' % (str(release)))
            os.chdir(temp)
            print('Bulding in %s' % temp)
            cmd = [os.path.join(self.location, 'configure'), '--prefix', l, '--disable-bootstrap']
            self.run_cmd(cmd, True)
            self.run_cmd('echo "MAKEINFO = :" >> Makefile')
            cmd = 'nice make -j10'
            # TODO: hack because of -j problem seen on 5.x releases
            if release.name.startswith('5.') and not release.name.startswith('5.4'):
                cmd = 'nice make'
            r = self.run_cmd(cmd)
            if r:
                self.run_cmd('make install')
            shutil.rmtree(temp)
        
    def build(self, install):
        for r in self.releases:
            self.build_release(r, install)

    def initialize_binaries(self):
        folders = os.listdir(self.install)
        existing = set()
        for f in folders:
            full = os.path.join(self.install, f, 'bin/gcc')
            if os.path.exists(full):
                h = strip_prefix(os.path.basename(f), 'gcc-')
                existing.add(h)

        for r in self.releases:
            if r.hash in existing:
                r.has_binary = True

        for r in self.latest:
            if r.hash in existing:
                r.has_binary = True

    def test(self, command, verbose, negate):
        print('Releases')
        for r in self.releases:
            r.test(self.install, command, verbose, negate)

        print('\nLatest revisions')
        for r in self.latest:
            if r.has_binary:
                r.run(self.install, command, verbose, negate)

    def run_cmd(self, command, strict = False):
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Build GCC binaries.')
    parser.add_argument('git', metavar = 'git', help = 'Location of git repository')
    parser.add_argument('install', metavar = 'install', help = 'Installation location')
    parser.add_argument('action', nargs = '?', metavar = 'action', help = 'Action', default = 'print', choices = ['print', 'build', 'test'])
    parser.add_argument('command', nargs = '?', metavar = 'command', help = 'GCC command')
    parser.add_argument('--verbose', action = 'store_true')
    parser.add_argument('--negate', action = 'store_true', help = 'FAIL if result code is equal to zero')

    args = parser.parse_args()
    g = GitRepository(args.git, args.install)

    if args.action == 'print':
        g.print()
    elif args.action == 'build':
        g.build(args.install)
    elif args.action == 'test':
        g.test(args.command, args.verbose, args.negate)
