#!/usr/bin/env python3

import fileinput
import json
import sys
import os
import subprocess

def find_binary(folder):
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f == 'cc1plus':
                return os.path.join(root, f)

    return None

if len(sys.argv) != 2:
    print('Usage: <folder>')
    exit(1)

results = []

for f in os.listdir(sys.argv[1]):
    full = os.path.join(sys.argv[1], f)
    if os.path.isdir(full):
        print(f)
        binary = find_binary(full)
        r = subprocess.check_output('~/Programming/buildbot-scripts/elf_info.py ' + binary, shell = True)
        data = json.loads(r)
        r = []
        for d in data:
            k = 'size' if 'size' in d else 'count'
            r.append((d['name'], d[k]))

        results.append((f, r))

results = sorted(results, key = lambda x: x[0], reverse = True)

print(';', end = '')
for key in results[0][1]:
    print(key[0] + ';' , end = '')
print()

for r in results:
    print(r[0] + ';', end = '')
    for i, key in enumerate(results[0][1]):
        print(str(r[1][i][1]) + ';', end = '')

    print()
