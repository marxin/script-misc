#!/usr/bin/env python3

import argparse
import concurrent.futures
import os
import shutil
import subprocess
from itertools import dropwhile, takewhile


def parse_default_targets(gcc_root):
    lines = open(os.path.join(gcc_root, 'contrib/config-list.mk')).read().splitlines()
    lines = list(dropwhile(lambda x: not x.startswith('LIST ='), lines))
    lines = list(takewhile(lambda x: x, lines))

    targets = ' '.join(lines)
    targets = targets.replace('\\', '')
    for t in targets.split(' ')[2:]:
        if t:
            yield t


JOBS = 4

parser = argparse.ArgumentParser(description='Batch build of GCC binaries')
parser.add_argument('repository', metavar='repository', help='GCC repository')
parser.add_argument('folder', metavar='folder', help='Folder where to build')
parser.add_argument('-t', '--targets', help='Targets to be built (comma separated)')
parser.add_argument('-p', '--preserve', action='store_true', help='Preserve built binaries')
args = parser.parse_args()

targets = list(parse_default_targets(args.repository))
if args.targets:
    targets = args.targets.split(',')

shutil.rmtree(args.folder, ignore_errors=True)
os.makedirs(args.folder)

log_dir = os.path.join(args.folder, 'logs')
os.makedirs(log_dir)
obj_dir = os.path.join(args.folder, 'objs')
os.makedirs(obj_dir)


def build_target(full_target):
    opts = ''
    target = full_target
    index = full_target.find('OPT')
    if index != -1:
        target = full_target[:index]
        opts = full_target[index + 3:].strip()

    with open(os.path.join(log_dir, full_target + '.stderr.log'), 'w') as err:
        with open(os.path.join(log_dir, full_target + '.stdout.log'), 'w') as out:
            d = os.path.join(obj_dir, full_target)
            os.mkdir(d)
            os.chdir(d)

            # 1) configure
            cmd = ('%s --target=%s --disable-bootstrap --enable-languages=c,c++ --disable-multilib %s --enable-obsolete'
                   % (os.path.join(args.repository, 'configure'), target, opts))
            cmd = cmd.strip()
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if r.returncode != 0:
                print(f'Configure FAILED for {full_target}')
                return

            out.write(r.stdout.decode('utf-8'))
            err.write(r.stderr.decode('utf-8'))

            # 2) build
            cmd = f'nice make -j{JOBS} all-host CXXFLAGS="-O0 -g" CFLAGS="-O0 -g"'
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, encoding='utf8')
            if r.returncode != 0:
                print(f'Target failed: {full_target}')

            out.write(r.stdout)
            err.write(r.stderr)

            # remove objdir if OK
            if r.returncode == 0 and not args.preserve:
                shutil.rmtree(d)
            print('D', end='', flush=True)


print(f'Total targets: {len(targets)}')
print('.' * len(targets))
with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = []
    for t in targets:
        futures.append(executor.submit(build_target, t))
    concurrent.futures.wait(futures)
    for future in futures:
        if future.exception():
            print(future.exception())
    print()
