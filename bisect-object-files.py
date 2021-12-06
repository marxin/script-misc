#!/usr/bin/env python3

import argparse
import os
import shutil
import sys

filename = 'FILES.txt'

parser = argparse.ArgumentParser(description='Drive bisection of object files.')
parser.add_argument('good_dir', help='Directory with good object files')
parser.add_argument('bad_dir', help='Directory with bad object files')
parser.add_argument('work_dir', help='Working directory where to copy files')
args = parser.parse_args()

if not os.path.exists(filename):
    print(f'File not found: {filename}')
    sys.exit(1)


bad_files = open(filename).read().splitlines()

# copy good files first
good_total = 0
for root, _, files in os.walk(args.good_dir):
    for file in files:
        if file not in bad_files and file.endswith('.o'):
            subpath = os.path.relpath(os.path.join(root, file), args.good_dir)
            shutil.copyfile(os.path.join(root, file), os.path.join(args.work_dir, subpath))
            good_total += 1

# then copy bad files
for file in bad_files:
    shutil.copyfile(os.path.join(args.bad_dir, file), os.path.join(args.work_dir, file))

print(f'Copied {good_total} good files and {len(bad_files)} bad files')
