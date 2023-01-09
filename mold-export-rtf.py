#!/usr/bin/env python3

import os
import sys
from pathlib import Path

sources = []

for root, _, files in os.walk(sys.argv[1]):
    for file in files:
        full = Path(root, file)
        fullname = str(full)
        if not fullname.endswith(('.cc', '.h')):
            continue
        elif fullname.startswith(('third-party', 'macho')):
            continue
        elif 'arch' in fullname and 'x86' not in fullname:
            continue
        elif 'win32' in fullname or 'source-all' in fullname:
            continue

        sources.append(full)


def file_priority(filename):
    if filename.endswith('.h'):
        if 'mold.h' in filename:
            p = 0
        else:
            p = 10
    else:
        p = 100

    if filename.startswith('elf/'):
        p += 1

    return p


sources = sorted(sources, key=lambda x: (file_priority(str(x)), x))

print('File count:', len(sources))


def cat_n(lines):
    for i, line in enumerate(lines):
        yield f'{i + 1:4d} {line}'


with open('source-all.cc', 'w') as w:
    w.write('/*\n')
    for i, source in enumerate(sources):
        loc = len(source.read_text().splitlines())
        w.write(f'  {i + 1}: {str(source).upper()} ({loc} LOC)\n')

    w.write('*/\n')
    w.write('\n')
    for i, source in enumerate(sources):
        lines = source.read_text().splitlines()
        lines = list(cat_n(lines))

        N = 60
        lines = ['', '/* ' + '#' * 60,
                 f'   {i + 1} / {len(sources)}: ' + str(source).upper(), '   ' + '#' * 60 + ' */', ''] + lines + ['']
        w.write('\n'.join(lines))
