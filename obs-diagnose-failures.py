#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import termcolor

parser = argparse.ArgumentParser(description = 'Analyze OBS log files')
parser.add_argument('location', help = 'Folder with logs')
parser.add_argument('--nocolor', action='store_true', help = 'Do not use colored output')
args = parser.parse_args()

def find_in_line(haystack, line):
    for needle in haystack:
        i = line.find(needle)
        if i != -1:
            p = termcolor.colored(needle, 'red', attrs = ['bold'])
            if args.nocolor:
                p = needle
            return line[:i] + p + line[i + len(needle):]

categories = [
        ('rpmlint threshold', ['----- Badness']),
        ('segfault', ['Segmentation fault', 'internal compiler error', 'Killed signal', 'lto1: fatal error']),
        ('multiple definition', ['multiple definition of']),
        ('Werror', ['[-Werror=']),
        ('FORTIFY_SOURCE', ['buffer overflow detected']),
        ('error', ['error:']),
        ('test-failure', ['test-suite.log] Error', 'test] Error', 'The following tests FAILED']),
        ('broken-build-system', ['No buildstatus set, either the base system is broken'])]

def find_diagnostics(lines):
    for c in categories:
        for l in lines:
            r = find_in_line(c[1], l)
            if r != None:
                return (c[0], r)

    return ('unknown error', None)

d = {}

for root, dirs, files in os.walk(args.location):
    for f in files:
        lines = [x.strip() for x in open(os.path.join(root, f)).readlines()]
        r = find_diagnostics(lines)
        if not r[0] in d:
            d[r[0]] = []

        d[r[0]].append((f + ' ' + root.split('/')[-1], r[1]))

for (k,v) in d.items():
    print('%25s: %5d' % (k, len(v)))

for c in categories:
    k = c[0]
    if not k in d:
        continue
    v = d[k]
    print('=== %s (%d) ===' % (k, len(v)))
    for p in sorted(v):
        if p[1] != None:
            print('%s:%s' % (p[0], p[1]))
        else:
            print(p[0])
