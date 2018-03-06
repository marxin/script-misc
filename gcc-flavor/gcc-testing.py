#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import os

from datetime import datetime

def average(values):
    return sum(values) / len(values)

parser = argparse.ArgumentParser(description='Batch GCC tester.')
parser.add_argument('install', help = 'Install prefix')
parser.add_argument('tmp', help = 'TMP folder')

args = parser.parse_args()

N = 5
tests = [('empty.c', 100),
        ('empty.C', 100),
        ('tramp3d-v4.ii -O2 -g', N),
        ('i386.ii', N),
        ('i386.ii -O2', N),
        ('i386.ii -O2 -g', N),
        ('insn-emit.ii -O2', N),
        ('generic-match.ii -O2', N),
        ('gimple-match.ii -O2', N)]

configurations = sorted([f for f in os.listdir(args.install) if os.path.isdir(os.path.join(args.install, f))])

# add system compiler
configurations.insert(0, '/usr/')

results = []
for c in configurations:
    results.append([])

for t in tests:
    print('=== TEST: %s iterations: %d ===' % (t[0], t[1]))
    first_time = None
    for i, c in enumerate(configurations):
        times = []
        for x in range(t[1]):
            start = datetime.now()
            subprocess.check_output('taskset 0x1 ' + os.path.join(args.install, c, 'bin/gcc') + ' -c ~/Documents/gcc-data-input/' + t[0] + ' -o /dev/null', shell = True)
            duration = datetime.now() - start
            times.append(duration.total_seconds())
        avg = average(times)
        if first_time == None:
            first_time = avg
        print('%-40s:%10.4fs:  %10.2f%%' % (c, avg, 100.0 * avg / first_time))
        results[i].append(avg)

print('\nResults:')
print(';', end = '')
for t in tests:
    print('%s-%dx;' % (t[0], t[1]), end = '')
print()

for i, c in enumerate(configurations):
    print(c + ';', end = '')
    for j, t in enumerate(tests):
        print(str(results[i][j]) + ';', end = '')
    print()
