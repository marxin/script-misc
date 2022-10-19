#!/usr/bin/env python3

import argparse
import subprocess

parser = argparse.ArgumentParser(description='Check GNU coding style with clang-format')
parser.add_argument('revision', help='Git revision to compare with', nargs='?', default='HEAD')
parser.add_argument('-i', '--inplace', action='store_true', help='Apply patch')
args = parser.parse_args()

contrib = '~/Programming/gcc/contrib/'
tmp = '/tmp/gcc.patch'

subprocess.check_output(f'git diff {args.revision} > {tmp}', shell=True)

if args.inplace:
    print('applying clang-format in place')
else:
    print('clang-format:')
subprocess.run('git diff -U0 --no-color %s | clang-format-diff -p1 %s | colordiff'
               % (args.revision, '-i' if args.inplace else ''), shell=True, encoding='utf8')

print()
print('check_GNU_style.py:')
subprocess.run(f'{contrib}/check_GNU_style.py {tmp}', shell=True, encoding='utf8')
