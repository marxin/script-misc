#!/usr/bin/env python3

import os
import subprocess
import sys

counter = 0
location = sys.argv[1]
needles = ['indirect_call', 'topn']

threshold = 0.5

if len(sys.argv) == 3:
    threshold = float(sys.argv[2])

print('Covered threshold: %.2f' % threshold)
print('== Stats for %s ==' % location)
for needle in needles:
    print('stats for %s:' % needle)
    histogram = {}
    counter_count = 0
    total_freq = 0
    total_freq_with_half = 0
    for root, dirs, files in os.walk(location):
        for f in files:
            if f.endswith('.gcda'):
                counter += 1
                full = os.path.join(root, f)
                r = subprocess.check_output('gcov-dump -l ' + full, encoding = 'utf8', shell = True)
                for l in r.split('\n'):
                    if needle in l:
                        counter_count += 1
                        values = [int(x) for x in l.split(':')[-1].split(' ') if x]
                        total = values[0]
                        total_freq += total
                        n = values[1]
                        values = values[2:]
                        assert len(values) == 2 * n
                        if not n in histogram:
                            histogram[n] = [0, 0, 0]
                        histogram[n][0] += 1
                        if values:
                            zipped = sorted(list(zip(values[::2], values[1::2])), key = lambda x: x[1], reverse = True)[:8]
                            for z in zipped:
                                if z[1] >= (threshold * total):
                                    histogram[n][1] += 1
                                    histogram[n][2] += z[1]
                                    total_freq_with_half += z[1]
                                    if n == 256:
                                        print('   ' + str(z))
                                elif n == 1:
                                    assert False

    print('Total: %d, total freq: %d, covered freq: %d (%.2f%%)' % (counter_count, total_freq, total_freq_with_half, 100.0 * total_freq_with_half / total_freq))
    print('Histogram:')
    for (k, v) in sorted(histogram.items(), key = lambda x: x[0]):
        print('  %4d tracked: %5d (%.2f%%), >=%.2f: %4d (cov. freq: %12d (%.2f%%))' % (k, v[0], 100.0 * v[0] / counter_count, threshold, v[1], v[2], 100.0 * v[2] / total_freq))
    print()
