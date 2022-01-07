#!/usr/bin/env python3

#
# The script can be used for more complex replacements in the source code.
#

import argparse
import concurrent.futures
import os
import re
import sys

EXTENSIONS = ('.h', '.c', '.cc', '.C', '.rst')


def handle_file_p(filename):
    if 'testsuite' in filename:
        return False
    if all(not filename.endswith(ext) for ext in EXTENSIONS):
        return False

    return True


FILES = [
    'insn-output.c', 'insn-recog.c', 'insn-emit.c', 'insn-extract.c', 'insn-peep.c',
    'insn-attrtab.c', 'insn-dfatab.c', 'insn-latencytab.c', 'insn-opinit.c', 'insn-preds.c',
    'insn-modes.c', 'insn-enums.c', 'insn-automata.c', '-checksum.c']

FILES += open('/tmp/files.txt').read().splitlines()
FILES.remove('main.c')

LOADED_FILES = [re.compile(fr'\b{re.escape(x)}\b') for x in FILES]


def modify_line(line, index, lines, filename):
    for x in LOADED_FILES:
        for match in reversed(list(re.finditer(x, line))):
            start = match.start()
            end = match.end()
            text = match.group()
            if text == 'gcc.c' and '-torture' in line:
                continue
            line = line[:start] + text + 'c' + line[end:]

    return line


parser = argparse.ArgumentParser(description='Make a custom replacements '
                                             'for source files')
parser.add_argument('directory', help='Root directory')
parser.add_argument('-v', action='store_true',
                    help='Verbose output')
parser.add_argument('-vv', action='store_true',
                    help='More verbose output')
args = parser.parse_args()

modified_files = 0

files_worklist = []

for root, _, files in os.walk(sys.argv[1]):
    for file in files:
        full = os.path.join(root, file)
        if handle_file_p(full):
            files_worklist.append(full)


def replace_file(full, i, n):
    if args.vv:
        print(f'.. {i + 1}/{len(files_worklist)}: {full}')

    modified = False
    try:
        modified_lines = []
        with open(full) as f:
            lines = f.readlines()
            for index, line in enumerate(lines):
                modified_line = modify_line(line, index, lines, full)
                if line != modified_line:
                    modified = True
                modified_lines.append(modified_line)
        if modified:
            with open(full, 'w') as w:
                w.write(''.join(modified_lines))
            if args.v:
                print(f'File modified: {full}')
            return True
    except UnicodeDecodeError as e:
        print(f'Skipping file: {full} ({e})')


with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = []
    for i, full in enumerate(files_worklist):
        futures.append(executor.submit(replace_file, full, i, len(files_worklist)))

    for future in futures:
        r = future.result()
        if r:
            modified_files += 1

if args.vv:
    print()
print(f'Visited files: {len(files_worklist)}')
print(f'Modified files: {modified_files}')
