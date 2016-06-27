#!/usr/bin/env python3

import sys
import hashlib
import argparse
import json
import os
import subprocess
import tempfile

from termcolor import colored

script_dirname = os.path.abspath(os.path.dirname(__file__))

class Release:
    def __init__(self, name, hash):
        self.name = name
        self.hash = hash
        self.have_binary = False

    def test(self, install, command, verbose):
        if not self.have_binary:
            print('  %s: missing binary' % self.name)
        else:
            self.run(install, command, verbose)

    def run(self, install, command, verbose):
        log = '/tmp/output'
        binary = os.path.join(install, 'gcc-' + self.hash, 'bin')
        cmd = binary + '/' + command
        with open(log, 'w') as out:
            r = subprocess.call(cmd, shell = True, stdout = out, stderr = out)
        text = colored('OK', 'green') if r == 0 else colored('FAILED', 'red')
        print('  %s: running command with result: %s' % (self.name, text))
        if verbose:
            print(open(log).read())

    def __str__(self):
        return self.name + ':' + self.hash

class Revision:
    def __init__(self, hash, author, timestamp, message):
        self.hash = hash
        self.message = message
        self.author = author
        self.timestamp = timestamp    
        self.have_binary = False

    def __str__(self):
        return self.hash + ':' + self.message

class GitRepository:
    def __init__(self, location):
        self.location = location
        self.releases = []
        self.latest = []
        os.chdir(location)
        self.parse_releases()
        self.parse_latest_revisions()

    def parse_releases(self):
        r = subprocess.check_output('git show-ref --tags', shell = True)

class GitRepository:
    def __init__(self, location):
        self.location = location
        self.releases = []
        self.latest = []
        os.chdir(location)
        self.parse_releases()
        self.parse_latest_revisions()

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
            version = name.lstrip('gcc-').rstrip('-release').replace('-', '.')

            if not any(map(lambda x: x.name == version, self.releases)):
                self.releases.append(Release(version, hash))

        self.releases = sorted(filter(lambda x: x.name >= '4.5.0', self.releases), key = lambda x: x.name)    

    def parse_latest_revisions(self, n = 1000):
        cmd = 'git log --pretty=format:"%H;%an;%aI;%s" parent/master~' + str(n) + '..parent/master'
        lines = subprocess.check_output(cmd, shell = True).decode('utf-8').split('\n')

        for l in lines:
            tokens = l.split(';')
            self.latest.append(Revision(tokens[0], tokens[1], tokens[2], tokens[3]))

    def print(self):
        for r in self.releases:
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
            self.run_cmd(cmd)
            self.run_cmd('echo "MAKEINFO = :" >> Makefile')
            r = self.run_cmd('nice make -j10')
            if r:
                self.run_cmd('make install')
        
    def build(self, install):
        for r in self.releases:
            self.build_release(r, install)

    def initialize_binaries(self, install):
        folders = os.listdir(install)
        existing = set()
        for f in folders:
            if os.path.exists(os.path.join(install, f, 'bin/gcc')):
                h = os.path.basename(f).lstrip('gcc-')
                existing.add(h)

        for r in self.releases:
            if r.hash in existing:
                r.have_binary = True

        for r in self.latest:
            if r.hash in existing:
                r.have_binary = True

    def test(self, install, command, verbose):
        self.initialize_binaries(install)

        for r in self.releases:
            r.test(install, command, verbose)

    def run_cmd(self, command):
        if isinstance(command, list):
            command = ' '.join(command)
        print('Running: %s' % command)
        try:
            with open('/tmp/gcc-build.stderr', 'w') as err:
                subprocess.check_output(command, shell = True, stderr = err)
            return True
        except subprocess.CalledProcessError as e:
            lines = e.output.decode('utf-8').split('\n')
            print('\n'.join(lines[-10:]))
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Build GCC binaries.')
    parser.add_argument('git', metavar = 'git', help = 'Location of git repository')
    parser.add_argument('install', metavar = 'install', help = 'Installation location')
    parser.add_argument('action', nargs = '?', metavar = 'action', help = 'Action', default = 'print', choices = ['print', 'build', 'test'])
    parser.add_argument('command', nargs = '?', metavar = 'command', help = 'GCC command')
    parser.add_argument('--verbose', action = 'store_true')

    args = parser.parse_args()
    g = GitRepository(args.git)

    if args.action == 'print':
        g.print()
    elif args.action == 'build':
        g.build(args.install)
    elif args.action == 'test':
        g.test(args.install, args.command, args.verbose)
