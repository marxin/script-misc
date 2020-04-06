#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import tempfile
import shutil

from termcolor import colored

parser = argparse.ArgumentParser(description = 'Diff object files in given foldes')
parser.add_argument('source1', help = 'Folder 1')
parser.add_argument('source2', help = 'Folder 2')
parser.add_argument('-d', '--diff', action = 'store_true', help = 'Print diff for different files')
parser.add_argument('-v', '--verbose', action = 'store_true', help = 'Verbose')
args = parser.parse_args()

def get_files(folder):
    if folder.endswith('/'):
        folder = folder[:-1]
    for root, dirs, files in os.walk(folder, topdown=False):
        for f in files:
            if f.endswith('.o'):
                full = os.path.join(root, f)
                assert full.startswith(folder)
                yield full[len(folder) + 1:]

def objdump(f):
    obj = '/tmp/objdfolderdiff-file.o'
    shutil.copyfile(f, obj)
    r = subprocess.check_output('objdump -S %s' % obj, shell = True, encoding = 'utf8')
    return r

def print_diff(f, source1, source2):
    f1 = os.path.join(args.source1, f + '.s.txt')
    f2 = os.path.join(args.source2, f + '.s.txt')

    with open(f1, 'w+') as f:
        f.write(source1)
    with open(f2, 'w+') as f:
        f.write(source2)

    subprocess.run('diff -u %s %s' % (f1, f2), shell = True)

source_files1 = list(sorted(get_files(args.source1)))
source_files2 = list(sorted(get_files(args.source2)))

if set(source_files1) != set(source_files2):
    print('List of files is not equal (%d/%d)' % (len(source_files1), len(source_files2)))

ret = 0
for i, f in enumerate(source_files1):
    s1 = objdump(os.path.join(args.source1, f))
    s2 = objdump(os.path.join(args.source2, f))
    if s1 != s2 or args.verbose:
        if s1 != s2:
            ret = 1
        print('%6d/%6d: %s: ' % (i, len(source_files1), f), end = '')
        print(colored('different', 'red') if s1 != s2 else colored('equal', 'green'))
        if args.diff:
            print_diff(f, s1, s2)

exit(ret)
