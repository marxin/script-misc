#!/usr/bin/env python3

import sys

if len(sys.argv) < 3:
    exit(1)

function = sys.argv[1]

for filename in sys.argv[2:]:
    print('Working on: %s' % filename, end='')
    lines = []
    in_func = False
    for line in open(filename).readlines():
        if ';; Function ' + function + ' ' in line:
            lines.append(line)
            in_func = True
        elif ';; Function ' in line and in_func:
            break
        elif in_func:
            lines.append(line)

    if lines:
        with open(filename, 'w+') as w:
            for line in lines:
                w.write(line)
        print(': wrote %d lines' % len(lines))
    else:
        print(': not modified')
