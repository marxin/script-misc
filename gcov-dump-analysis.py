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

    allways_used_values = [0] * 5
    allways_used_values_freq = [0] * 5
    allways_used_values_hit = [0] * 5
    all_used_values = [0] * 5
    all_used_values_freq = [0] * 5
    all_used_values_hit = [0] * 5
    used_values = [0] * (TOPN_COUNTERS + 1)
    used_values_freq = [0] * (TOPN_COUNTERS + 1)
    used_values_hit = [0] * (TOPN_COUNTERS + 1)
    nonrep_used_values = [0] * 5
    nonrep_used_values_freq = [0] * 5
    nonrep_used_values_hit = [0] * 5
    all_with_missing_vals = []
    with_missing_vals = 0
    with_missing_vals_freq = 0
    not_executed = 0
    one = 0
    one_freq = 0
    sum = 0
    allways_sum = 0
    all_sum = 0
    rep_sum = 0
    nonrep_sum = 0

    i = 0
    c = len(all) / TOPN_COUNTER_VALUES
    while i < c:
        topn = all[TOPN_COUNTER_VALUES * i: TOPN_COUNTER_VALUES * (i + 1)]
        sum += abs (topn[0])
        if topn[0] == 0:
            not_executed += 1
            i += 1
            continue
        if topn[0] < 0:
            with_missing_vals += 1
            with_missing_vals_freq += abs (topn[0])
            all_with_missing_vals.append(topn)
        match = False
        for j in range(TOPN_COUNTERS):
            if topn[2 * j + 2] == topn[0] * TOPN_COUNTERS:
                match = True
        if match and topn[0] != 0:
            if topn[0] < 0:
                print (error)
            one += 1
            one_freq += topn[0]
        else:
            allways_used = 0
            all_used = 0
            used = 0
            nonrep_used = 0
            allways_hit = 0
            all_hit = 0
            hit = 0
            nonrep_hit = 0
            for j in range(TOPN_COUNTERS):
                if topn[2 * j + 2] > abs (topn[0]) / 2:
                    allways_used += 1
                    allways_sum += abs (topn[2 * j + 2])
                    allways_hit += abs (topn[2 * j + 2])
                if topn[0] > 0 and abs (topn[2 * j + 2]) > abs (topn[0]) / 2:
                    all_used += 1
                    all_sum += abs (topn[2 * j + 2])
                    all_hit += abs (topn[2 * j + 2])
                if abs (topn[2 * j + 2]) > abs (topn[0]) / 2:
                    nonrep_used += 1
                    nonrep_sum += abs (topn[2 * j + 2])
                    nonrep_hit += abs (topn[2 * j + 2])
                if (topn[2 * j + 2] > 0 or topn[0] > 0) and abs (topn[2 * j + 2]) > abs (topn[0]) / 2:
                    used += 1
                    rep_sum += abs (topn[2 * j + 2])
                    hit += abs (topn[2 * j + 2])
            allways_used_values[allways_used] += 1
            allways_used_values_freq[allways_used] += abs (topn[0])
            allways_used_values_hit[allways_used] += allways_hit
            all_used_values[all_used] += 1
            all_used_values_freq[all_used] += abs (topn[0])
            all_used_values_hit[all_used] += all_hit
            used_values[used] += 1
            used_values_freq[used] += abs (topn[0])
            used_values_hit[used] += hit
            nonrep_used_values[nonrep_used] += 1
            nonrep_used_values_freq[nonrep_used] += abs (topn[0])
            nonrep_used_values_hit[nonrep_used] += nonrep_hit

        i += 1

    print('stats for %s:' % needle)
    print('  total: %d freq: %d' % (len(all) / TOPN_COUNTER_VALUES, sum))
    print('  not executed at all: %d' % (not_executed))
    print('  with missing vals: %d (%2.2f%%) freq:%d (%2.2f%%)' % (with_missing_vals, 100 * with_missing_vals / c, with_missing_vals_freq, 100 * with_missing_vals_freq / sum))
    print('  only one target: %d (%2.2f%%) freq:%d (%2.2f%%)' % (one, 100 * one / c, one_freq, 100 * one_freq / sum))
    print('  useful values (with not one target):')
    for i in range(TOPN_COUNTERS + 1):
        f = allways_used_values_hit[i]*100/allways_used_values_freq[i]/TOPN_COUNTERS if allways_used_values_freq[i] else 0
        print('    %d allways winning values: %8d times (%2.2f%%) freq:%12d (%2.2f%%) hitrate: (%2.2f%%)' % (i, allways_used_values[i], 100.0 * allways_used_values[i] / c, allways_used_values_freq[i], 100 * allways_used_values_freq[i] / sum, f))
    print('  total hitrate in all runs: freq:%d (%2.2f%%)' % (one_freq + allways_sum/TOPN_COUNTERS, 100 * (one_freq + allways_sum/TOPN_COUNTERS) / sum))
    for i in range(TOPN_COUNTERS + 1):
        f = all_used_values_hit[i]*100/all_used_values_freq[i]/TOPN_COUNTERS if all_used_values_freq[i] else 0
        print('    %d all reproducible values: %8d times (%2.2f%%) freq:%12d (%2.2f%%) hitrate: (%2.2f%%)' % (i, all_used_values[i], 100.0 * all_used_values[i] / c, all_used_values_freq[i], 100 * all_used_values_freq[i] / sum, f))
    print('  total hitrate with all counters valid: freq:%d (%2.2f%%)' % (one_freq + all_sum/TOPN_COUNTERS, 100 * (one_freq + all_sum/TOPN_COUNTERS) / sum))
    for i in range(TOPN_COUNTERS + 1):
        f = used_values_hit[i]*100/used_values_freq[i]/TOPN_COUNTERS if used_values_freq[i] else 0
        print('    %d some reroducible values: %8d times (%2.2f%%) freq:%12d (%2.2f%%) hitrate: (%2.2f%%)' % (i, used_values[i], 100.0 * used_values[i] / c, used_values_freq[i], 100 * used_values_freq[i] / sum, f))
    print('  total hitrate with some counters valid: freq:%d (%2.2f%%)' % (one_freq + rep_sum/TOPN_COUNTERS, 100 * (one_freq + rep_sum/TOPN_COUNTERS) / sum))
    for i in range(TOPN_COUNTERS + 1):
        f = nonrep_used_values_hit[i]*100/nonrep_used_values_freq[i]/TOPN_COUNTERS if nonrep_used_values_freq[i] else 0
        print('    %d non-reproducible values: %8d times (%2.2f%%) freq:%12d (%2.2f%%) hitrate: (%2.2f%%)' % (i, nonrep_used_values[i], 100.0 * nonrep_used_values[i] / c, nonrep_used_values_freq[i], 100 * nonrep_used_values_freq[i] / sum, f))
    print('  total hitrate predicted non-reproducibly: freq:%d (%2.2f%%)' % (one_freq + nonrep_sum/TOPN_COUNTERS, 100 * (one_freq + nonrep_sum/TOPN_COUNTERS) / sum))
    print()

    """
    N = 10
    print('Top %d with missing vals counters:' % N)
    all_with_missing_vals = list(sorted(all_with_missing_vals, key = lambda x: -x[0], reverse = True))
    for i in range(N):
        print('  freq: %.2f%%: %s' % (100 * all_with_missing_vals[i][0] / sum, all_with_missing_vals[i]))
    print()
    print()
    """
