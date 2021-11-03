#!/usr/bin/env python3

import os
import sys

files = sys.argv[1]
cwd = os.getcwd()

with open('FILES.txt', 'w') as f:
    for file in files.split():
        f.write(os.path.join(cwd, file) + '\n')
