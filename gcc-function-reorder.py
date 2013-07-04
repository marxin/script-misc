#!/usr/bin/env python

from __future__ import print_function
import os
import sys

if len(sys.argv) != 4:
  print('gcc-function-reorder <binary> <gcc_dump> <callgrind_dump>')
  exit(1)

f = os.popen('readelf --wide -s ' + sys.argv[1])

### read elf parsing ###
readelf_functions = []

for line in f.readlines():
  items = [x for x in line.strip().split(' ') if x] + [line.strip()]

  if len(items) > 5 and items[0][-1] is ':' and items[0][:-1].isdigit() and items[3] == 'FUNC' and items[2] != '0':
    readelf_functions.append(items[7])

### gcc log parsing ###

gcc_dump = []

f = open(sys.argv[2])

for line in f:
  l = line.rstrip()
  if len(l) > 0 and l[0] != ' ':
    gcc_dump.append(line[0:l.index('/')])

for x in gcc_dump:
  if x not in readelf_functions:
    print('WARNING: gcc func is missing in readelf: %s' % x)

### callgrind parsing ###

callgrind_functions = []

f = open(sys.argv[3])

for line in f:
  callgrind_functions.append(line.strip())

### PHASE 1: readelf and callgrind dump comparison

called_in_gcc = []

total = len(readelf_functions)
found1 = 0
found2 = 0

for i in callgrind_functions:
  if i in readelf_functions:
    found1 += 1

  if i in gcc_dump:
    called_in_gcc.append(i)
    found2 += 1

print('Total: %u, found in readelf: %u, found in gcc: %u' % (total, found1, found2))

exit(0)

seen = set()

for i in called_in_gcc:
  if i not in seen:
    print(i, file = sys.stderr)
  seen.add(i)
