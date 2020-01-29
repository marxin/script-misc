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
    size_comparison = 100.0 * p[6] / p[5] if p[5] else 0
    print('%30s%6d / %6ds%10.2f%% %10s / %10s %10.2f%%' % (p[0], p[1], p[3], p[4], sizeof_fmt(p[5]), sizeof_fmt(p[6]), size_comparison))

def print_header():
    print('%30s%6s / %6s%11s %10s / %10s %10s' % ('Package', 'dwz', 'Total', 'Ratio', 'Size before', 'Size after', 'Ratio'))

def sizeof_fmt(num):
    for x in ['B','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0

d = sys.argv[1]
files = os.listdir(d)

have_dwz_size = 0
for f in files:
    lines = [l.strip() for l in open(os.path.join(d, f)).readlines()]
    r = None
    size = [0, 0]
    for i, l in enumerate(lines):
        if ' dwz: ' in l and not 'is not a shared library' in l and not 'too much work for irq' in l:
            print('WARNING:%s:%s' % (f, l))
        t = 'original debug info size'
        if t in l:
            tokens = l[len(t):].split(' ')
            # TODO
            a = tokens[2][:-1]
            b = tokens[6]
            if a.endswith('kB'):
                a = a[:-2]
            if b.endswith('kB'):
                b = b[:-2]
            size = [1024 * int(a), 1024 * int(b)]
            have_dwz_size += 1
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
        r += size
        results.append(r)

s = sum([x[1] for x in results])
l = len(results)

N = 50

print()
print('Top %d by time:' % N)
print_header()
for r in sorted(results, key = lambda x: x[1], reverse = True)[:N]:
    print_package(r)

print()
print('Top %d by percentage of package build time:' % N)
print_header()
for r in sorted(results, key = lambda x: x[4], reverse = True)[:N]:
    print_package(r)

print()
print('Top %d by size of package debug info size:' % N)
print_header()
for r in sorted(results, key = lambda x: x[5], reverse = True)[:N]:
    print_package(r)

total_time = sum([x[3] for x in results])
print()
print('Total time: %ds (%.2f %%) of %d packages (of %d), average: %.2fs, total package build time: %ds' % (s, 100.0 * s / total_time, l, len(files), 1.0 * s / l, total_time))
print()

total_size_before = sum([x[5] for x in results])
total_size_after = sum([x[6] for x in results])

print('Total size before: %s, after: %s (%.2f%%), have dwz stats for %d packages' % (sizeof_fmt(total_size_before), sizeof_fmt(total_size_after), 100.0 * total_size_after / total_size_before, have_dwz_size))
