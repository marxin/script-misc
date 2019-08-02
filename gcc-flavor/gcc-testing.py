#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import os

from datetime import datetime

def average(values):
    return sum(values) / len(values)

parser = argparse.ArgumentParser(description='Batch GCC tester.')
parser.add_argument('compiler', help = 'Path to compiler')

args = parser.parse_args()

N = 1
tests = [('empty.c', 100),
        ('empty.C', 100),
        ('tramp3d-v4.ii -O2 -g', N),
        ('i386.ii', N),
        ('i386.ii -O2', N),
        ('i386.ii -O2 -g', N),
        ('insn-emit.ii -O2', N),
        ('generic-match.ii -O2', N),
        ('gimple-match.ii -O2', N),
        ('kdecore.ii -O2 -g', N)]

results = []
for t in tests:
    times = []
    for x in range(t[1]):
        start = datetime.now()
        subprocess.check_output('taskset 0x1 %s --param inline-unit-growth=20 -c ./gcc-data-input/%s -o /dev/null' % (args.compiler, t[0]), shell = True)
        duration = datetime.now() - start
        times.append(duration.total_seconds())
    avg = average(times)
    print('%s-%sx:%f' % (t[0], t[1], avg))
    results.append(avg)

print('\nResults:')
print(';', end = '')
for t in tests:
    print('%s-%dx;' % (t[0], t[1]), end = '')
print()

for j, t in enumerate(tests):
    print(str(results[j]) + ';', end = '')
print()
