#!/usr/bin/env python

from __future__ import print_function
import os
import sys

if len(sys.argv) != 4:
  print('gcc-function-reorder <binary> <gcc_dump> <callgrind_dump>')
  exit(1)

f = os.popen('./readelf_sorted_symbols.py ' + sys.argv[1])

### read elf parsing ###
readelf_functions = []
readelf_lines = []

for line in f.readlines():
  tokens = line.strip().split(' ')
  readelf_functions.append(tokens[-1])
  readelf_lines.append(line.strip())

### gcc log parsing ###
### line sample: 'main:2:'

gcc_dump = {}

f = open(sys.argv[2])

for line in f:
  l = line.rstrip()

  if l[-1] == ':':
    tokens = l.split(':')
    order = int(tokens[1])
    if order > 0:
      gcc_dump[tokens[0]] = order

for x in gcc_dump:
  if x not in readelf_functions:
    print('WARNING: gcc func is missing in readelf: %s' % x)

### callgrind parsing ###
# line format: INIT:<function_name>
# Function is met multiple times

callgrind_functions = []
callgrind_dict = {}

f = open(sys.argv[3])

for line in f:
  line = line.strip()
  if line.startswith('INIT:'):
    fname = line[5:]
    if fname not in callgrind_dict:
      callgrind_dict[fname] = 1
      callgrind_functions.append(fname)
    else:
      callgrind_dict[fname] = callgrind_dict[fname] + 1

### PHASE 1: readelf and callgrind dump comparison

total = len(readelf_functions)
found1 = 0
found2 = 0
called_once = 0

d_visited = set()
d_missing = set()

print()
for i in callgrind_functions:
  if i in readelf_functions:
    found1 += 1
    if callgrind_dict[i] == 1:
      called_once += 1

  if i in gcc_dump:
    d_visited.add(i)
    found2 += 1
  elif i in readelf_functions:
    d_missing.add(i)
    print('WARNING: gcc func is missing in gcc dump: %s' % i)

print()
print('Total: %u, found in readelf: %u, found in gcc: %u' % (total, found1, found2))
print('Called one: %u' % called_once)

for line in readelf_lines:
  f = line.split(' ')[-1]

  print(line, end = '', file = sys.stderr)

  if f in gcc_dump:
    print(' [SORTED:%s]' % gcc_dump[f], file = sys.stderr, end = '')

  if f in d_missing:
    print(' [NOT_SEEN]', file = sys.stderr, end = '')

  print(file = sys.stderr)
