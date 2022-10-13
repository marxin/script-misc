#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import termcolor

# SUSE_Factory_Head/x86_64/hydrogen.log:[  202s] /home/abuild/rpmbuild/BUILD/hydrogen-1.0.0-beta1/src/gui/src/widgets/Rotary.cpp:68:1: warning:   when initialized here [-Wreorder]

class Warning:
    def __init__(self, line):
        original = line
        i1 = line.find(':')
        self.package = line[:i1]
        self.package = self.package[self.package.rfind('/')+1:]
        line = line[i1:]
        i2 = line.find('s] ')

        tokens = [' warning: ', ' Warning: ', ' error: ']
        self.location = None
        for t in tokens:
            i3 = line.find(t)
            if i3 != -1:
                self.location = line[i2 + 3:i3 - 1]
                break
        if self.location == None:
            self.warning = None
            return
        line = line[i3:]
        i4 = line.find(' [-W')
        self.warning = line[i4 + 2:-1]

        assert self.warning != ''

    def print(self):
        print(self.package)
        print(self.location)
        print(self.warning)

parser = argparse.ArgumentParser(description = 'Analyze OBS log warnings')
parser.add_argument('warnings', help = 'File with warnings')
args = parser.parse_args()

warnings = {}

for l in open(args.warnings).readlines():
    l = l.strip()
    if not l.endswith(']'):
        continue
    w = Warning(l)
    if w.warning == None:
        continue
    if not w.package in warnings:
        warnings[w.package] = {}
    if not w.warning in warnings[w.package]:
        warnings[w.package][w.warning] = set()
    warnings[w.package][w.warning].add(w.location)

bywarning = {}
bypackage = {}

for k, v in warnings.items():
    bypackage[k] = 0
    for k2, v2 in v.items():
        bypackage[k] += len(v2)
        if not k2 in bywarning:
            bywarning[k2] = 0
        bywarning[k2] += len(v2)

total = 0
for k, v in sorted(bywarning.items(), key = lambda x: x[1], reverse = True):
    print('%-40s: %d' % (k, v))
    total += v
print('\nTotal warnings: %d' % total)

for k, v in sorted(bypackage.items(), key = lambda x: x[1], reverse = True):
    print('%-40s: %d' % (k, v))
    total += v
