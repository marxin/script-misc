#!/usr/bin/env python3

import glob
import subprocess

for f in sorted(glob.glob('*.dot')):
    print(f)
    subprocess.check_output(f'dot -Tsvg {f} -o {f}.svg', shell=True)
