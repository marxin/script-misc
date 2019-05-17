#!/usr/bin/env python3

# Sample:
# alias stmt walking                 :  28.75 ( 17%)   0.12 ( 12%)  28.81 ( 17%)  186428 kB ( 18%)

import argparse
import subprocess
import shutil
import os
import termcolor

parser = argparse.ArgumentParser(description = 'Time report diff')
parser.add_argument('source', help = 'Source time report')
parser.add_argument('target', help = 'Targettime report')
args = parser.parse_args()

limit = 0.03

def parse_lines(f, filter):
    d = {}
    for l in open(f).readlines():
        l = l.rstrip()
        if l.startswith(' '):
            tokens = l.split(':')
            time = float(tokens[1].strip().split(' ')[0])
            d[tokens[0].strip()] = time

    total = d['TOTAL']
    if filter:
        for k in list(d.keys()):
            if d[k] < total * limit:
                del d[k]

    return d

s = parse_lines(args.source, True)
t = parse_lines(args.target, False)

print('PASS;Before;After;Change')
for (k, v) in sorted(s.items(), key = lambda x: x[1]):
    print('%s;%.2f;%.2f;%.2f%%' % (k, v, t[k], 100.0 * t[k] / v))

