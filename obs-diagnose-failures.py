#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import termcolor

parser = argparse.ArgumentParser(description = 'Analyze OBS log files')
parser.add_argument('location', help = 'Folder with logs')
parser.add_argument('--verbose', help = 'Verbose', action='store_true')
args = parser.parse_args()

def find_in_line(haystack, line):
    for needle in haystack:
        i = line.find(needle)
        if i != -1:
            return line[:i] + termcolor.colored(needle, 'red', attrs = ['bold']) + line[i + len(needle):]

categories = [('segfault', ['Segmentation fault', 'internal compiler error', 'Killed signal']),
        ('Werror', ['[-Werror=']),
        ('error', ['error:']),
        ('test-failure', ['test-suite.log] Error', 'test] Error', 'The following tests FAILED']),
        ('broken-build-system', ['No buildstatus set, either the base system is broken'])]

def find_diagnostics(lines):
    for l in lines:
        for c in categories:
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

        d[r[0]].append((f + '/' + root.split('/')[-1], r[1]))

for (k,v) in d.items():
    print('%25s: %5d' % (k, len(v)))

if args.verbose:
    for c in categories:
        v = d[c[0]]
        print('=== %s (%d) ===' % (c[0], len(v)))
        for p in sorted(v):
            if p[1] != None:
                print('%s:%s' % (p[0], p[1]))
            else:
                print(p[0])
