#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os

parser = argparse.ArgumentParser(description = 'Analyze OBS log files')
parser.add_argument('location', help = 'Folder with logs')
parser.add_argument('--verbose', help = 'Verbose', action='store_true')
parser.add_argument('--curl', '-c', help = 'Generate CURL bugzilla requests', action='store_true')
args = parser.parse_args()

def is_segfault(line):
    if 'Segmentation fault' in line or 'internal compiler error' in line:
        return True
    return False

def is_werror(line):
    if 'error:' in line and not 'Bad exit status from' in line and '-Werror=' in line:
        return True
    return False

def is_error(line):
    if 'error:' in line and not 'Bad exit status from' in line:
        return True
    return False

def is_post_build_error(line):
    if ' E: ' in line:
        return True
    return False

def find_diagnostics(lines):
    for l in lines:
        for d in [('segfault', is_segfault), ('Werror', is_werror), ('error', is_error), ('post-build-check', is_post_build_error)]:
            if d[1](l):
                return (d[0], l)

    return ('unknown error', None)

d = {}

for root, dirs, files in os.walk(args.location):
    for f in files:
        lines = [x.strip() for x in open(os.path.join(root, f)).readlines()]
        r = find_diagnostics(lines)
        if not r[0] in d:
            d[r[0]] = []

        d[r[0]].append((f, r[1]))

for (k,v) in d.items():
    print('%16s: %5d' % (k, len(v)))

if args.verbose:
    for (k,v) in d.items():
        print('=== %s ===' % k)
        for p in v:
            if p[1] != None:
                print('%s:%s' % (p[0], p[1]))
            else:
                print(p[0])

header = 'GCC 8: XXX build fails'

body = """
Build the package with GCC 8, there's error:

XXX

Please build the project as follows to reproduce the issue:
osc build --alternative-project=openSUSE:Factory:Staging:Gcc7
""".strip()

if args.curl:
    for (k,v) in d.items():
        for p in v:
            if p[1] != None:
                print(header.replace('XXX', p[0].rstrip('.log')))
                print(body.replace('XXX', p[1]))

