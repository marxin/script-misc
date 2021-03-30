#!/usr/bin/env python3

import os
import subprocess
import sys

OUTPUT = 'FILES.txt'
files = sys.argv[1:]
CWD = os.getcwd()
output = []

for f in files:
    if f.endswith('.a'):
        objects = subprocess.check_output(f'ar t {f}', shell=True, encoding='utf8').splitlines()
        for o in objects:
            output.append(os.path.join(CWD, o))
    else:
        output.append(os.path.join(CWD, f))

with open(OUTPUT, 'w') as f:
    f.write('\n'.join(output))

print(f'{len(output)} written to {OUTPUT}')
