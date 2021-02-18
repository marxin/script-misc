#!/usr/bin/env python3

import argparse
import os
import re

from itertools import *
from difflib import unified_diff

parser = argparse.ArgumentParser(description = 'Print difference for 2 runs with PGO')
parser.add_argument('gcda1')
parser.add_argument('gcda2')
parser.add_argument('gcno')
args = parser.parse_args()

fnregex = re.compile('.*FUNCTION ident=([0-9]*), .*')

def belongs_to_fn(line):
    if 'magic' in line or 'stamp' in line or 'PROGRAM_SUMMARY' in line or 'FUNCTION' in line:
        return False
    else:
        return True

def fn_start(line):
    return fnregex.match(line) != None

def parse_gcda(filename):
    fns = {}
    lines = [l[l.find(':') + 1:].rstrip() for l in open(filename).readlines()]

    while(len(lines) > 0):
        lines = list(dropwhile(lambda x: not fn_start(x), lines))
        fn = lines[0]
        ident = int(fnregex.match(fn).group(1))
        lines = lines[1:]
        body = list(takewhile(belongs_to_fn, lines))
        lines = lines[len(body):]
        fns[ident] = (body, fn.split(' '))
    return fns

f1  = parse_gcda(args.gcda1)
f2  = parse_gcda(args.gcda2)
gcno = parse_gcda(args.gcno)

for ident in f1:
    if f1[ident][0] != f2[ident][0]:
        no = gcno[ident][1]
        location = no[-1].split(':')
        print('Difference for fn %d (%s %s:%s)' % (ident, no[-2][1:-1], location[0], location[1]))

        a = [x + '\n' for x in f1[ident][0]]
        b = [x + '\n' for x in f2[ident][0]]
        print(''.join(unified_diff(a, b)))
