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

tests = ['empty.c',
        'empty.C',
        'i386.ii',
        'i386.ii -O2',
        'i386.ii -O2 -g',
        'insn-emit.ii -O2',
        'generic-match.ii -O2',
        'gimple-match.ii -O2']

configurations = sorted([f for f in os.listdir(args.install) if os.path.isdir(os.path.join(args.install, f))])

# add system compiler
configurations.insert(0, '/usr/')

for t in tests:
    first_time = None
    for i, c in enumerate(configurations):
        times = []
        for i in range(3):
            start = datetime.now()
            subprocess.check_output('taskset 0x1 ' + os.path.join(args.install, c, 'bin/gcc') + ' -c ~/Documents/gcc-data-input/' + t, shell = True)
            duration = datetime.now() - start
            times.append(duration.total_seconds())
        avg = average(times)
        if first_time == None:
            first_time = avg
        print('%30s:%30s:%10.4fs:  %10.2f%%' % (c, t, avg, 100.0 * avg / first_time))
