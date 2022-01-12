#!/usr/bin/env python3

import os
import subprocess
import sys

OUTPUT = '/tmp/files.txt'
candidates = []

EXCLUDES = ('s-oscons-tmplt.c', 'raise-gcc.c', 'terminals.c', 'targext.c', 'adaint.c',
            'cal.c', 'errno.c', 'sysdep.c', 'ctrl_c.c', 'vms-ar.c', 'vms-ld.c')

for folder in sys.argv[1:]:
    for root, _, files in os.walk(folder):
        for file in files:
            full = os.path.join(root, file)
            add = True

            for exclude in EXCLUDES:
                if exclude in full:
                    add = False
            for needle in ('testsuite', 'docs/examples/'):
                if needle in full:
                    add = False
            if not full.endswith('.c'):
                add = False

            if add:
                candidates.append(full)

candidates = sorted(candidates)
filenames = set()

for i, candidate in enumerate(candidates):
    filenames.add(candidate.split('/')[-1])
    print(f'{i + 1}/{len(candidates)}: {candidate}')
    if len(sys.argv) >= 3 and sys.argv[-1] == '--rename':
        subprocess.check_output(f'git mv {candidate} {candidate}c', shell=True, encoding='utf8')

with open(OUTPUT, 'w') as f:
    for filename in sorted(filenames):
        f.write(f'{filename}\n')

print('Candidates:', len(candidates))
print(f'Saved {len(filenames)} to {OUTPUT}')
