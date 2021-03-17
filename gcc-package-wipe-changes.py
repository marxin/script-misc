#!/usr/bin/env python

import sys

filename = sys.argv[1]

lines = open(filename).read().splitlines()
if (len(lines) >= 5 and lines[0].startswith('---') and lines[2] == '' and lines[4] == ''
        and lines[3].startswith('- Bump to ')):
    with open(filename, 'w') as f:
        f.write('\n'.join(lines[5:]) + '\n')
