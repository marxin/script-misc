#!/usr/bin/env python3

import os
import subprocess
import sys

counter = 0
location = sys.argv[1]
needles = ['indirect_call', 'topn']

threshold = 0.25
max_nodes = 32
interesting_coverage = .3

if len(sys.argv) == 3:
    threshold = float(sys.argv[2])

print('Covered threshold: %.2f' % threshold)
print('== Stats for %s ==' % location)
for needle in needles:
    print('stats for %s:' % needle)
    histogram = {}
    full_counters = []
    counter_count = 0
    total_freq = 0
    total_freq_with_half = 0
    total_tuples = 0
    missing_freq = 0
    for root, dirs, files in os.walk(location):
        for f in files:
            if f.endswith('.gcda'):
                counter += 1
                full = os.path.join(root, f)
                r = subprocess.check_output('gcov-dump -l -r ' + full, encoding = 'utf8', shell = True)
                for l in r.split('\n'):
                    if needle in l:
                        if ' 0 counts' in l:
                            continue
                        allvalues = [int(x) for x in l.split(':')[-1].split(' ') if x]
                        while allvalues:
                            if len(allvalues) == 1:
                                print('WARNING: ' + l)
                                break
                            counter_count += 1
                            n = allvalues[1]
                            values = allvalues[:2 + 2 * n]
                            allvalues = allvalues[len(values):]
                            total = values[0]
                            total_freq += total
                            total_tuples += n
                            values = values[2:]
                            if len(values) != 2 * n:
                                print('WARNING: %s' + l)
                                break
                            if not n in histogram:
                                histogram[n] = [0, 0, 0]
                            histogram[n][0] += 1
                            if values:
                                zipped = sorted(list(zip(values[::2], values[1::2])), key = lambda x: x[1], reverse=True)
                                s = sum(x[1] for x in zipped)
                                if s > total:
                                    print('WARNING: strange: %s' % l)
                                    break
                                missing_freq += total - s
                                if n == max_nodes:
                                    full_counters.append((total, s, zipped))
                                for z in zipped:
                                    if z[1] >= (threshold * total):
                                        histogram[n][1] += 1
                                        histogram[n][2] += z[1]
                                        total_freq_with_half += z[1]
                                    elif n == 1:
                                        assert False

    print('Total: %d, total freq: %d, covered freq: %d (%.2f%%), missing freq: %d (%.2f%%)' % (counter_count, total_freq,
        total_freq_with_half, 100.0 * total_freq_with_half / total_freq, missing_freq, 100.0 * missing_freq / total_freq))
    print('Total tuples: %d (size before: 9*N=%d, after: 2*N + (2*TUPLE_COUNT)=%d'
            % (total_tuples, 9 * counter_count, 2 * counter_count + 2 * total_tuples))
    print('Histogram:')
    for (k, v) in sorted(histogram.items(), key = lambda x: x[0]):
        print('  %4d tracked: %7d (%2.2f%%), >=%.2f: %4d (cov. freq with prevailing: %12d (%.2f%%))' % (k, v[0], 100.0 * v[0] / counter_count, threshold, v[1], v[2], 100.0 * v[2] / total_freq))
    print(f'    full counters (>={interesting_coverage}%):')
    for full in sorted(full_counters, key=lambda x: x[1], reverse=True):
        covered_freq = 100.0 * full[1] / total_freq
        if covered_freq >= interesting_coverage:
            print(f'      total: {full[1]} ({covered_freq:.2f}%), prevailing counter: {100.0 * full[2][0][1] / full[0]:.2f}%')
    print()
