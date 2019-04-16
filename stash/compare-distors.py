#!/usr/bin/env python3

from ltodata import *

comparison = ['GCC 7', 'GCC 8']

a = set(factory.keys())
b = set(gcc8.keys())

keys = sorted([x for x in b & a if not 'modules' in x and not 'grub' in x and not 'firmware' in x])

def get_size(d):
    for k in d:
        if k['name'] == 'elf':
            return int(k['size'])

    assert False

total_s1 = 0
total_s2 = 0

results = []

for k in keys:
    s1 = get_size(factory[k])
    s2 = get_size(gcc8[k])
    total_s1 += s1
    total_s2 += s2
    results.append((k, s1, s2))

results.append(('TOTAL', total_s1, total_s2))

print(';' + ';'.join(comparison))
for r in sorted(results, key = lambda x: x[1], reverse = True):
    print('%s;%d;%d;%.2f%%' % (r[0], r[1], r[2], 100.0 * r[2] / r[1]))
