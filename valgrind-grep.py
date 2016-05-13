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

class Section:
    def __init__(self, name, f):
        self.name = name
        self.f = f
        self.count = 0
        self.errors = []
    def matches(self, bt):
        return any(map(self.f, e.bt))
    def add(self, e, count):
        self.errors.append([e, count])
        self.count += count

sections = [
    Section('gfortran', lambda x: 'gfc_' in x in x),
    Section('c++', lambda x: 'cp_parser_' in x or 'cp_fold_' in x),
    Section('c', lambda x: 'c_parser_' in x),
    Section('c-common', lambda x: 'c_common_init_options' in x),
    Section('Other', lambda x: True)
]

total_errors = 0
total_types = 0

groups = list(map(lambda g: [g[0], len(list(g[1]))], groupby(sorted(errors))))
for g in groups:
    e = g[0]
    total_types += 1
    total_errors += g[1]

    for s in sections:
        if s.matches(e.bt):
            s.add(e, g[1])
            break

for s in sections:
    print('== SECTION: %s ==' % s.name)
    print('==   error types: %d, total errors: %d' % (len(s.errors), s.count))
    print('==   error types: %2.2f%%, total errors: %2.2f%%' % (100.0 * len(s.errors) / total_types, 100.0 * s.count / total_errors))
    print('')

    for e in sorted(s.errors, key = lambda x: x[1], reverse = True):
        print('%s: %d occurences' % (e[0].name, e[1]), end = '')
        print(e[0].bt_str())
        print()

print('== Statistics ==')
# TODO

# print(error.name + ':' + str(len(list(g))))
