#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
from termcolor import colored

buffer = ''

def printme(string):
    global buffer
    buffer += string + '\n'
    print(string)

def create_dir(path):
    if os.path.exists(path):
        return
    os.makedirs(path)

tokens = ['error: ', 'internal compiler error: ', ' FAILED ']
extra_lines = 1

def grep_errors(log):
    lines = log.split('\n')
    for i, v in enumerate(lines):
        if any(map(lambda x: x in v, tokens)):
            v = ['  ' + x for x in lines[i - 1: i + 1]]
            printme('\n'.join(v))

def process_arch(url, folder, project, repository, arch):
    create_dir(os.path.join(folder, repository))
    arch_dir = os.path.join(folder, repository, arch)

    result = subprocess.check_output('osc -A %s r %s -r %s -a %s --csv' % (url, project, repository, arch), shell = True)
    packages = result.decode('utf-8', 'ignore').strip().split('\n')
    packages = [x.split(';')[0] for x in packages if 'failed' in x]
    packages = [x for x in packages if x != '_']

    print('Packages: %d' % len(packages))

    create_dir(arch_dir)
    for index, package in enumerate(sorted(packages)):
        for i in range(3):
            try:
                result = subprocess.check_output('osc -A %s remotebuildlog %s %s %s %s' % (url, project, package, repository, arch), shell = True)
                log = result.decode('utf-8', 'ignore')
                log_file = os.path.join(arch_dir, package + '.log')
                with open(log_file, 'w+') as w:
                    w.write(log)
                printme('%d/%d: %s' % (index, len(packages), package))
            except Exception as e:
                print(e)

            break

parser = argparse.ArgumentParser(description = 'Download OBS log files for failed packages')
parser.add_argument('url', help = 'OBS API url')
parser.add_argument('folder', help = 'Destination folder')
parser.add_argument('project', help = 'OBS project name')
parser.add_argument('repository', help = 'Repository name')
parser.add_argument('archs', nargs = '+', help = 'Architectures')
args = parser.parse_args()

shutil.rmtree(args.folder, ignore_errors = True)

for arch in args.archs:
    printme('== %s ==' % arch)
    process_arch(args.url, args.folder, args.project, args.repository, arch)

with open(os.path.join(args.folder, 'build.log'), 'w+') as w:
    w.write(buffer)
