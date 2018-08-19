#!/usr/bin/env python3

import os
import sys

from itertools import *

results = []

def get_time(l):
    assert l[0] == '['
    l = l[1:]
    l = l[:l.find('s')]
    return int(l.strip())

def print_package(p):
    print('%30s%6d / %6ds%10.2f%%' % (p[0], p[1], p[3], p[4]))

d = sys.argv[1]
files = os.listdir(d)

for f in files:
    lines = [l.strip() for l in open(os.path.join(d, f)).readlines()]
    r = None
    for i, l in enumerate(lines):
        if 'dwz: ' in l and not 'is not a shared library' in l and not 'too much work for irq' in l:
            print('WARNING:%s:%s' % (f, l))
        if 'sepdebugcrcfix' in l:
            start = get_time(lines[i - 1])
            end = get_time(l)
            assert end >= start
            r = [f, end - start]
            break

    fn = lambda x: 'extracting debug info from' in x
    extracting = list(takewhile(fn, dropwhile(lambda x: not fn(x), lines)))

    if len(extracting) and r != None:
        r.append(get_time(extracting[-1]) - get_time(extracting[0]))

    if r != None:
        for l in reversed(lines):
            if 's]' in l:
                r.append(get_time(l))
                r.append(round(100.0 * r[1] / r[3], 2))
                break
        results.append(r)

s = sum([x[1] for x in results])
l = len(results)

N = 50

print()
print('Top %d by time:' % N)
for r in sorted(results, key = lambda x: x[1], reverse = True)[:N]:
    print_package(r)

print()
print('Top %d by percentage of package build time:' % N)
for r in sorted(results, key = lambda x: x[4], reverse = True)[:N]:
    print_package(r)

total_time = sum([x[3] for x in results])
print()
print('Total time: %ds (%.2f %%) of %d packages (of %d), average: %.2fs, total package build time: %ds' % (s, 100.0 * s / total_time, l, len(files), 1.0 * s / l, total_time))
print()
