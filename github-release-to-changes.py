#!/usr/bin/env python3

import sys

LIMIT = 80

for line in sys.stdin.read().strip().splitlines():
    print('  * ', end='')
    first = True
    while line:
        if not first:
            print('    ', end='')
        if len(line) <= LIMIT:
            print(line, end='')
            line = None
            break
        else:
            end = LIMIT
            while line[end] != ' ':
                end -= 1
            print(line[:end])
            line = line[end + 1:]
            first = False
    print()
