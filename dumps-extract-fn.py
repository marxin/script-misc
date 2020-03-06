#!/usr/bin/env python3

import sys

if len(sys.argv) < 3:
    exit(1)

function = sys.argv[1]

for filename in sys.argv[2:]:
    print('Working on: %s' % filename, end = '')
    lines = []
    in_func = False
    for l in open(filename).readlines():
        if ';; Function ' + function + ' ' in l:
            lines.append(l)
            in_func = True
        elif ';; Function ' in l and in_func:
            break
        elif in_func:
            lines.append(l)

    if lines:
        with open(filename, 'w+') as w:
            for l in lines:
                w.write(l)
        print(': wrote %d lines' % len(lines))
    else:
        print(': not modified')
