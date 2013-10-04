#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import tempfile

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
### line sample: 'Balanced map symbol order:main:2'

gcc_dump = {}

f = open(sys.argv[2])

for line in f:
  tokens = line.rstrip().split(':')

  if(len(tokens) > 2 and tokens[0].startswith('Balanced map symbol order')):
    gcc_dump[tokens[-2]] = int(tokens[-1])

"""
for x in gcc_dump:
  if x not in readelf_functions:
    print('WARNING: gcc func is missing in readelf: %s' % x)
"""

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

callgrind_functions_filtered = [x for x in callgrind_functions if x in readelf_functions]

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
print('Total: %u, found in ELF: %u, found in gcc: %u' % (total, found1, found2))
print('Called once: %u' % called_once)

offsets_seen_in_gcc = set()

for line in readelf_lines:
  items = [x for x in line.strip().split(' ') if x]
  f = items[-1]

  if f in gcc_dump and gcc_dump[f] > 0:
    offsets_seen_in_gcc.add(items[0])

"""
for line in readelf_lines:
  f = line.split(' ')[-1]

  print(line, end = '', file = sys.stderr)

  if f in gcc_dump:
    print(' [SORTED:%s]' % gcc_dump[f], file = sys.stderr, end = '')
  elif f in readelf_functions:
    print(' [NOT_SEEN]', file = sys.stderr, end = '')
  else:
    print(' [IGNORE]', file = sys.stderr, end = '')

  print(file = sys.stderr)
"""

t = tempfile.mkstemp(suffix = '.html', prefix = 'gcc_dump_')

style = '* { margin: 0; padding: 0; font-family: "Trebuchet MS"; font-size: 10pt; } table thead { background-color: green; color: white; font-weight: bold; } .not-seen { background-color: rgb(240,240,240); } .seen-nonzero { background-color: rgb(153, 204, 0); } .seen-zero { background-color: orange; } .cell-6 { font-weight: bold; } .cell-7 { font-weight: bold; } .called { background-color: rgb(0, 153, 255); }'

os.write(t[0], '<html><head><style>' + style + '</style></head><body><table><thead><tr><td>Value</td><td>Size</td><td>Type</td><td>Bind</td><td>Vis</td><td>Ndx</td><td>Valgrind idx</td><td>Profile order</td><td>Name</td></tr><thead><tbody>\n')

for line in readelf_lines:
  items = [x for x in line.strip().split(' ') if x]
  f = items[-1]
  func_order = -1
  cls = ''

  if f in gcc_dump:
    func_order = gcc_dump[f]

  if func_order == -1:
    cls = 'not-seen'
  elif func_order == 0:
    cls = 'seen-zero'
  else:
    cls = 'seen-nonzero'

  if func_order <= 0 and items[0] in offsets_seen_in_gcc:
    continue

  os.write(t[0], '<tr class="%s">\n' % cls)

  callgrind_index = callgrind_functions_filtered.index(f) if f in callgrind_functions_filtered else -1

  items.insert(6, str(callgrind_index))
  items.insert(7, str(func_order))

  for (idx, item) in enumerate(items):
    if idx == 6:
      os.write(t[0], '<td class="cell-%d %s">%s</td>\n' % (idx, 'called' if callgrind_index > 0 else '', item))
    else:
      os.write(t[0], '<td class="cell-%d">%s</td>\n' % (idx, item))

  os.write(t[0], '</tr>\n')

os.write(t[0], '\n')
os.write(t[0], '</tbody></table></body></html>\n')

os.close(t[0])
print('HTML report file: ' + t[1])
