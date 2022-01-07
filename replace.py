#!/usr/bin/env python3

#
# The script can be used for more complex replacements in the source code.
#

import argparse
import concurrent.futures
import os
import sys

EXTENSIONS = ('.h', '.c', '.cc', '.C', '.rst')


def handle_file_p(filename):
    if 'testsuite' in filename:
        return False
    if all(not filename.endswith(ext) for ext in EXTENSIONS):
        return False

    return True


def modify_line(line, index, lines, filename):
    # Example replacement:
    # m = re.match(r'.*time_function\(&([^,]*),', line)
    # if m:
    #    e = m.end(1)
    #    name = m.group(1)
    #    line = line[:e + 1] + f' "{name}",' + line[e + 1:]

    # Example replacement for filenames
    # for x in FILES:
    #    for match in reversed(list(re.finditer(x, line))):
    #        start = match.start()
    #        end = match.end()
    #        text = match.group()
    #        line = line[:start] + text + 'c' + line[end:]

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
    global modified_files
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
            modified_files += 1
            if args.v:
                print(f'File modified: {full}')
    except UnicodeDecodeError as e:
        print(f'Skipping file: {full} ({e})')


with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = []
    for i, full in enumerate(files_worklist):
        futures.append(executor.submit(replace_file, full, i, len(files_worklist)))

    for future in futures:
        future.result()

if args.vv:
    print()
print(f'Visited files: {len(files_worklist)}')
print(f'Modified files: {modified_files}')
