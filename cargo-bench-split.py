#!/usr/bin/env python3

import sys

for line in open(sys.argv[1]):
    if 'ns/iter' in line:
        parts = [x for x in line.split() if x]
        print(f"{parts[1]}:{parts[4].replace(',', '')}")
