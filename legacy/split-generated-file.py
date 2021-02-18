#!/usr/bin/env python3

from itertools import *

N = 8

def chunkify(lst,n):
    return [lst[i::n] for i in range(n)]

lines = [x.rstrip() for x in open('insn-emit.c').readlines()]

print(len(lines))

header = list(takewhile(lambda x: not x.startswith('// header'), lines))
lines = lines[len(header) + 1:]

parts = []

while len(lines) > 0:
    bunch = list(takewhile(lambda x: not x.startswith('// marker'), lines))
    parts.append(bunch)
    lines = lines[len(bunch) + 1:]

chunks = chunkify(parts, N)

# generate parts
for i in range(len(chunks)):
    with open('insn-emit-%d.c' % i, 'w') as w:
        w.write('\n'.join(header))
        for p in chunks[i]:
            w.write('\n'.join(p))
