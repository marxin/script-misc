#!/usr/bin/env python3

from operator import *
import subprocess
import sys

output = subprocess.check_output('nm ' + sys.argv[1], shell = True, encoding = 'utf8')

symbols = []
for line in output.split('\n'):
    if line.startswith('0000'):
        address = int(line.split(' ')[0], 16)
        symbols.append((address, line))

for line in sorted(symbols, key = itemgetter(0)):
    print(line[1])
