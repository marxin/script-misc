#!/usr/bin/env python3

import os
import sys
import re

from itertools import groupby

known_types = [
    'are possibly lost',
    'are definitely lost',
    'Conditional jump or move depends on uninitialised value(s)',
    'Use of uninitialised value of size',
    'Invalid read of size'
    ]

class BackTrace:
    def __init__(self, lines):
        self.name = None
        for t in known_types:
            if t in lines[0]:
                self.name = t

        if self.name == None:
            self.name = lines[0]

        self.bt = []
        for line in lines[1:]:
            self.bt.append(re.sub('.*: ', '', line))

    def bt_str(self):
        return '\n  '.join([''] + self.bt)

    def __str__(self):
        return self.name + self.bt_str()

    def __lt__(self, other):
        return str(self) < str(other)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self)

if len(sys.argv) <= 1:
    print('usage: valgrind-grep [file]')
    exit(-1)

lines = map(lambda x: re.sub('^==[0-9]*==', '', x.strip()), filter(lambda x: x.startswith('=='), open(sys.argv[1]).readlines()))

bt = []
errors = []

for line in lines:
    if line == '':
        if len(bt) > 0:
            errors.append(BackTrace(bt))
        bt = []
    else:
        bt.append(line)

groups = list(map(lambda g: [g[0], len(list(g[1]))], groupby(sorted(errors))))
for g in sorted(groups, key = lambda x: x[1], reverse = True):
    e = g[0]
    print('%s: %d occurences' % (e.name, g[1]), file = sys.stderr, end = '')
    print(e.bt_str(), file = sys.stderr)
    print('', file = sys.stderr)

print('== Statistics ==')
print('Total number of errors: %d' % len(errors))
print('Number of different errors: %d' % len(groups))

# print(error.name + ':' + str(len(list(g))))
