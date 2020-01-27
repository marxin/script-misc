#!/usr/bin/env python3

import os
import subprocess
import sys

counter = 0
location = sys.argv[1]
needles = ['indirect_call', 'topn']

TOPN_COUNTERS = 4

if len(sys.argv) == 3:
    TOPN_COUNTERS = int(sys.argv[2])

TOPN_COUNTER_VALUES = 2 * TOPN_COUNTERS + 1

print('== Stats for %s ==' % location)
for needle in needles:
    all = []
    for root, dirs, files in os.walk(location):
        for f in files:
            if f.endswith('.gcda'):
                counter += 1
                full = os.path.join(root, f)
                r = subprocess.check_output('gcov-dump -l ' + full, encoding = 'utf8', shell = True)
                buffer = None
                for l in r.split('\n'):
                    if not ':' in l:
                        continue
                    l = l[l.find(':') + 1:].strip()
                    if 'COUNTERS' in l:
                        if buffer:
                            assert len(buffer) % TOPN_COUNTER_VALUES == 0
                            all += buffer
                        buffer = None
                    if needle in l:
                        buffer = []
                    elif ':' in l and buffer != None:
                        parts = l.split(':')
                        assert len(parts) == 2
                        values = [int(x) for x in parts[1].strip().split(' ')]
                        buffer += values

    used_values = [0] * (TOPN_COUNTERS + 1)
    used_values_freq = [0] * (TOPN_COUNTERS + 1)
    all_invalid = []
    invalid = 0
    invalid_freq = 0
    not_executed = 0
    one = 0
    one_freq = 0
    sum = 0

    i = 0
    c = len(all) / TOPN_COUNTER_VALUES
    while i < c:
        topn = all[TOPN_COUNTER_VALUES * i: TOPN_COUNTER_VALUES * (i + 1)]
        sum += topn[0]
        if topn[0] == 0:
            not_executed += 1
            i += 1
            continue
        if topn[2] == -1 or topn[2] == -9223372036854775808:
            invalid += 1
            invalid_freq += topn[0]
            all_invalid.append(topn)
        else:
            match = False
            for j in range(TOPN_COUNTERS):
                if topn[2 * j + 2] == topn[0] * TOPN_COUNTERS:
                    match = True
            if match and topn[0] != 0:
                one += 1
                one_freq += topn[0]
            else:
                used = 0
                for j in range(TOPN_COUNTERS):
                    if topn[2 * j + 2] > topn[0] / 2:
                        used += 1
                used_values[used] += 1
                used_values_freq[used] += topn[0]

        i += 1

    print('stats for %s:' % needle)
    print('  total: %d freq: %d' % (len(all) / TOPN_COUNTER_VALUES, sum))
    print('  not executed at all: %d' % (not_executed))
    print('  invalid: %d (%2.2f%%) freq:%d (%2.2f%%)' % (invalid, 100 * invalid / c, invalid_freq, 100 * invalid_freq / sum))
    print('  only one target: %d (%2.2f%%) freq:%d (%2.2f%%)' % (one, 100 * one / c, one_freq, 100 * one_freq / sum))
    print('  useful values (with not one target):')
    for i in range(TOPN_COUNTERS + 1):
        print('    %d values: %8d times (%2.2f%%) freq:%12d (%2.2f%%)' % (i, used_values[i], 100.0 * used_values[i] / c, used_values_freq[i], 100 * used_values_freq[i] / sum))
    print()

    N = 10
    print('Top %d invalid counters:' % N)
    all_invalid = list(sorted(all_invalid, key = lambda x: x[0], reverse = True))
    for i in range(N):
        print('  freq: %.2f%%: %s' % (100 * all_invalid[i][0] / sum, all_invalid[i]))
