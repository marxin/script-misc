#!/usr/bin/env python3

# Parses and compares 2 files made by 'nm --size-sort'

import sys
from pathlib import Path


def prune_fname(name):
    for N in ('.lto_priv', '.cold', '.part', '.isra', '.constprop', '.llvm.'):
        if N in name:
            name = name[:name.index(N)]
    return name


def parse(path):
    symbols = {}

    lines = path.open().read().splitlines()
    for line in lines:
        size, t, name = line.split()
        size = int(size, 16)
        name = prune_fname(name)
        if t not in ('t', 'T'):
            continue

        if name not in symbols:
            symbols[name] = 0
        symbols[name] += size

    return symbols


sfile = Path(sys.argv[1])
dfile = Path(sys.argv[2])

source = parse(sfile)
dest = parse(dfile)

print('      symbols size')
print(sfile.stem + ':', len(source), sum(source.values()))
print(dfile.stem + ':', len(dest), sum(dest.values()))
print()

same_names = 0
different_size1 = 0
different_size2 = 0
diffs = []

verbose = len(sys.argv) >= 4 and sys.argv[3] == '-v'

for symname, size in source.items():
    if symname in dest:
        same_names += 1
        diffs.append((symname, dest[symname] - size))
    else:
        different_size1 += size
        if verbose:
            print('>', symname)

for symname, size in dest.items():
    if symname not in source:
        different_size2 += size
        if verbose:
            print('<', symname)

print('Common symbols:', same_names)
# print('Different size:', different_size1, different_size2)

diffs = sorted(diffs, key=lambda x: x[1], reverse=True)

wins = 0
loses = 0

for d in diffs:
    v = d[1]
    if v < 0:
        wins += v
    else:
        loses += v

print('wins:', wins, 'loses:', loses, 'DIFF:', wins + loses)
