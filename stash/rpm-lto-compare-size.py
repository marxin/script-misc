#!/usr/bin/env python3

import os
import subprocess
import json
from os.path import join, getsize

def analyze_folder(folder):
    allfiles = []

    for root, dirs, files in os.walk(folder):
        for f in files:
            allfiles.append(join(root, f))

    elfs = []
    for i, f in enumerate(allfiles):
        r = subprocess.check_output('file "%s"' % f, shell = True, encoding = 'utf8')
        if 'ELF' in r:
            elfs.append(f)
        print('%d/%d: %s' % (i, len(allfiles), r.strip()))

    d = {}

    for i, e in enumerate(elfs):
        r = subprocess.check_output('~/Programming/buildbot-scripts/elf_info.py %s' % e, shell = True, encoding = 'utf8')
        name = e[len(folder):]
        d[name] = json.loads(r)
        print('%d/%d' % (i, len(elfs)))

    return d

lto = analyze_folder('/tmp/binaries-lto')
nonlto = analyze_folder('/tmp/binaries')

print(len(lto.keys()))
print(len(nonlto.keys()))

common = set(lto.keys()) & set(nonlto.keys())
print('common:' + str(len(common)))

keys = ':'.join(x['name'] for x in list(lto.items())[0][1])
print('ELF file:%s:%s' % (keys, keys))

for c in sorted(common):
    wo = ':'.join([str(x['count']) if 'count' in x else str(x['size']) for x in nonlto[c]])
    w = ':'.join([str(x['count']) if 'count' in x else str(x['size']) for x in lto[c]])
    print('%s:%s::%s' % (c, wo, w))
