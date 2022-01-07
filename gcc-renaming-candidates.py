#!/usr/bin/env python3

import os
import sys

OUTPUT = '/tmp/files.txt'
candidates = []

for root, _, files in os.walk(sys.argv[1]):
    for file in files:
        full = os.path.join(root, file)
        add = True
        for needle in ('testsuite', 'docs/examples/'):
            if needle in full:
                add = False
        if not full.endswith('.c'):
            add = False

        if add:
            candidates.append(full)

candidates = sorted(candidates)
filenames = set()

for candidate in candidates:
    filenames.add(candidate.split('/')[-1])
    print(candidate)

with open(OUTPUT, 'w') as f:
    for filename in sorted(filenames):
        f.write(f'{filename}\n')

print('Candidates:', len(candidates))
print(f'Saved {len(filenames)} to {OUTPUT}')
