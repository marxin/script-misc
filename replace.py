#!/usr/bin/env python3

#
# The script can be used for more complex replacements in the source code.
#

import argparse
import os
import sys

EXTENSIONS = ('.h', '.c', '.cc', '.C')


def handle_file_p(filename):
    if 'testsuite' in filename:
        return False
    if all(not filename.endswith(ext) for ext in EXTENSIONS):
        return False

    return True


def modify_line(line, index, lines):
    # Example replacement:
    # m = re.match(r'.*time_function\(&([^,]*),', line)
    # if m:
    #    e = m.end(1)
    #    name = m.group(1)
    #    line = line[:e + 1] + f' "{name}",' + line[e + 1:]

    return line


parser = argparse.ArgumentParser(description='Make a custom replacements '
                                             'for source files')
parser.add_argument('directory', help='Root directory')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Verbose output')
args = parser.parse_args()

visited_files = 0
modified_files = 0

for root, _, files in os.walk(sys.argv[1]):
    for file in files:
        full = os.path.join(root, file)
        if not handle_file_p(full):
            continue

        visited_files += 1

        modified = False
        try:
            modified_lines = []
            with open(full) as f:
                lines = f.readlines()
                for index, line in enumerate(lines):
                    modified_line = modify_line(line, index, lines)
                    if line != modified_line:
                        modified = True
                    modified_lines.append(modified_line)
            if modified:
                with open(full, 'w') as w:
                    w.write(''.join(modified_lines))
                modified_files += 1
                if args.verbose:
                    print(f'File modified: {full}')
        except UnicodeDecodeError as e:
            print(f'Skipping file: {full} ({e})')


print(f'Visited files: {visited_files}')
print(f'Modified files: {modified_files}')
