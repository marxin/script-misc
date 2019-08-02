#!/usr/bin/env python3

import sys
from itertools import *

token = ':COUNTERS'
arcs_token = 'COUNTERS arcs'

lines = [l.strip() for l in open(sys.argv[1]).readlines()]

def find_groups(lines):
    while len(lines) > 0:
        l0 = lines[0]
        lines = lines[1:]
        chunk = list(takewhile(lambda x: not token in x, lines))
        yield [l0] + chunk
        lines = lines[len(chunk):]

groups = list([x for x in find_groups(lines) if arcs_token in x[0]])

all_values = []

for g in groups:
    arcs = int(g[0].split(' ')[-2])
    values = []
    for v in g[1:]:
        values += [int(x) for x in v.split(':')[-1].strip().split(' ')]
    assert len(values) == arcs
    all_values += values

keys = set(all_values)

print('histogram')
histogram = []
for k in sorted(keys, reverse = True):
    c = len([x for x in all_values if x == k])
    histogram.append((k, c))

for h in histogram:
    print('%5d: %5d' % (h[0], h[1]))

percentile = 0.999
arcs_sum = sum(all_values)

print('arcs: %d, sum: %d' % (len(all_values), arcs_sum))

acc = 0
cut = False
for h in histogram:
    acc += h[0] * h[1]
    f = acc / arcs_sum
    print('with %10d we have coverage: %.6f%%' % (h[0], 100.0 * f))
    if not cut and f > percentile:
        cut = True
        print('======= percentile met: %.2f%% ====' % (100 * percentile))
