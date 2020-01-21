#!/usr/bin/env python3

import os
import subprocess
import sys

all = []
counter = 0

location = sys.argv[1]
needles = ['indirect_call', 'topn']

print('== Stats for %s ==' % location)
for needle in needles:
    for root, dirs, files in os.walk(location):
        for f in files:
            if f.endswith('.gcda'):
                counter += 1
                full = os.path.join(root, f)
                # print('%d:%s' % (counter, full))
                r = subprocess.check_output('gcov-dump -l ' + full, encoding = 'utf8', shell = True)
                buffer = None
                for l in r.split('\n'):
                    if not ':' in l:
                        continue
                    l = l[l.find(':') + 1:].strip()
                    if 'COUNTERS' in l:
                        if buffer:
                            assert len(buffer) % 9 == 0
                            all += buffer
                        buffer = None
                    if needle in l:
                        buffer = []
                    elif ':' in l and buffer != None:
                        parts = l.split(':')
                        assert len(parts) == 2
                        values = [int(x) for x in parts[1].strip().split(' ')]
                        buffer += values

    used_values = [0] * 5
    invalid = 0

    i = 0
    c = len(all) / 9
    while i < c:
        topn = all[9 * i: 9 * (i + 1)]
        if topn[2] == -1:
            invalid += 1
        else:
            used = 0
            for j in range(4):
                if topn[2 * j + 2] != 0:
                    used += 1
            used_values[used] += 1

        i += 1

    print('stats for %s:' % needle)
    print('  total: %d' % (len(all) / 9))
    print('  invalid: %d' % (invalid))
    print('  tracked values:')
    for i in range(5):
        print('    %d values: %8d times (%.2f%%)' % (i, used_values[i], 100.0 * used_values[i] / c))
    print()
