#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
from termcolor import colored
import concurrent.futures

def create_dir(path):
    if os.path.exists(path):
        return
    os.makedirs(path)

tokens = ['error: ', 'internal compiler error: ', ' FAILED ']

parser = argparse.ArgumentParser(description = 'Download OBS log files for failed packages')
parser.add_argument('url', help = 'OBS API url')
parser.add_argument('folder', help = 'Destination folder')
parser.add_argument('project', help = 'OBS project name')
parser.add_argument('repository', help = 'Repository name')
parser.add_argument('archs', nargs = '+', help = 'Architectures')
parser.add_argument('-a', '--all', action = 'store_true', help = 'Get all, not only failing')
parser.add_argument('-t', '--threads', type=int, help = 'Limit threads to N')
parser.add_argument('-p', '--progress', action='store_true', help = 'Show progress')
args = parser.parse_args()

if not args.threads:
    args.threads = 64

shutil.rmtree(args.folder, ignore_errors = True)

def download_build_log(package, log_file):
    global done
    if args.progress:
        print(package[0], end='', flush=True)
    result = subprocess.check_output('osc -A %s remotebuildlog %s %s %s %s' % (args.url, args.project, package, args.repository, arch), shell = True, encoding='utf8')
    with open(log_file, 'w+') as w:
        w.write(result)

def process_arch(arch):
    create_dir(os.path.join(args.folder, args.repository))
    arch_dir = os.path.join(args.folder, args.repository, arch)

    result = subprocess.check_output('osc -A %s r %s -r %s -a %s --csv' % (args.url, args.project, args.repository, arch), shell = True)
    packages = result.decode('utf-8', 'ignore').strip().split('\n')
    packages = [x.split(';')[0] for x in packages if 'failed' in x or (args.all and 'succeeded' in x)]
    packages = [x for x in packages if x != '_']

    print('Packages: %d' % len(packages))

    create_dir(arch_dir)
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for package in packages:
            log_file = os.path.join(arch_dir, package + '.log')
            futures.append(executor.submit(download_build_log, package, log_file))
        concurrent.futures.wait(futures)
        for future in futures:
            if future.exception():
                print(future.exception())
        print()

for arch in args.archs:
    process_arch(arch)
