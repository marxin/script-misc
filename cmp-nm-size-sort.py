#!/usr/bin/env python

# Parses and compares 2 files made by 'nm --size-sort'

import sys


def prune_fname(name):
    for N in ('.lto_priv', '.cold', '.part', '.isra'):
        if N in name:
            name = name[:name.index(N)]
    return name


def parse(path):
    symbols = {}

    lines = open(path).read().splitlines()
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


default = parse(sys.argv[1])
lto = parse(sys.argv[2])

print('def', len(default), sum(default.values()))
print('LTO', len(lto), sum(lto.values()))

same_names = 0
diffs = []

for symname, size in default.items():
    if symname in lto:
        same_names += 1
        diffs.append((symname, lto[symname] - size))

print('Common symbols:', same_names)

diffs = sorted(diffs, key=lambda x: x[1], reverse=True)
print('')

wins = 0
loses = 0

for d in diffs:
    v = d[1]
    if v < 0:
        wins += v
    else:
        loses += v

print('wins:', wins, 'loses:', loses, 'diff:', wins + loses)
