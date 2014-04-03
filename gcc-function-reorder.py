#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import tempfile

def is_thunk(name):
  return name.startswith('_ZThn')

def get_thunk_parent(name):
  parent = '_Z' + name[(name[1:].index('_') + 2):]
  return parent

if len(sys.argv) != 4:
  print('gcc-function-reorder <binary> <gcc_dump> <callgrind_dump>')
  exit(1)

f = os.popen(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'readelf_sorted_symbols.py') + ' ' + sys.argv[1])

### read elf parsing ###
readelf_functions = []
readelf_lines = []

for line in f.readlines():
  tokens = line.strip().split(' ')
  readelf_functions.append(tokens[-1])
  readelf_lines.append(line.strip())

### gcc log parsing ###
### line execute: grep expand_all_function library.so.ltrans*

gcc_dump = {}
gcc_dump_partition = {}
gcc_dump_list = []

f = open(sys.argv[2])

for line in f:
  tokens = line.strip().split(':')
  func = tokens[-2]
  order = int(tokens[-1])

  gcc_dump[func] = order
  gcc_dump_partition[func] = tokens[0].split('.')[-3]
  gcc_dump_list.append([func, order])

"""
  if(len(tokens) > 2 and tokens[0].startswith('Balanced map symbol order')):
    func = tokens[-2]
    order = int(tokens[-1])
"""

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
    if not is_thunk(i):
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

style = '* { margin: 0; padding: 0; font-family: "Trebuchet MS"; font-size: 10pt; } table thead { background-color: green; color: white; font-weight: bold; } .not-seen { background-color: rgb(240,240,240); } .seen-nonzero { background-color: rgb(153, 204, 0); } .seen-zero { background-color: orange; } .cell-7 { font-weight: bold; } .cell-8 { font-weight: bold; } .called { background-color: rgb(0, 153, 255); }'

os.write(t[0], '<html><head><style>' + style + '</style></head><body><table><thead><tr><td>#</td><td>Value</td><td>B value</td><td>Size</td><td>Type</td><td>Bind</td><td>Vis</td><td>Ndx</td><td>Valgrind idx</td><td>Profile order</td><td>LTO partition</td><td>Status</td><td>Name</td></tr><thead><tbody>\n')

counter = 0
for line in readelf_lines:
  counter += 1
  items = [x for x in line.strip().split(' ') if x]
  f = items[-1]
  func_order = -1
  cls = ''

  if f in gcc_dump:
    func_order = gcc_dump[f]

  if func_order <= 0 and items[0] in offsets_seen_in_gcc:
    continue

  callgrind_index = callgrind_functions_filtered.index(f) if f in callgrind_functions_filtered else -1
  note = ''

  missing = '_MISSING_'

  if callgrind_index > 0:
    note = missing if func_order <= 0 else '_VALGRIND_'

  # thunks

  if missing and is_thunk(f): 
    target = get_thunk_parent(f)
    if target in gcc_dump:
      func_order = gcc_dump[target]
    
    note = '_THUNK_'

  # profile is missing
  if func_order <= 0 and callgrind_index > 0 and not is_thunk(f):
    print('ORDER missing: ' + f)

  if note == '':
    continue

  if func_order == -1:
    cls = 'not-seen'
  elif func_order == 0:
    cls = 'seen-zero'
  else:
    cls = 'seen-nonzero'

  os.write(t[0], '<tr class="%s">\n' % cls)

  items.insert(6, str(callgrind_index))
  items.insert(7, str(func_order))

  # partition
  partition = ''

  if f in gcc_dump_partition:
    partition = gcc_dump_partition[f]

  items.insert(8, str(partition))

  items.insert(9, note)

  # offset in bytes
  items.insert(1, int(items[0], 16))

  items.insert(0, str(counter))

  for (idx, item) in enumerate(items):
    if idx == 8:
      os.write(t[0], '<td class="cell-%d %s">%s</td>\n' % (idx, 'called' if callgrind_index > 0 else '', item))
    else:
      os.write(t[0], '<td class="cell-%d">%s</td>\n' % (idx, item))

  os.write(t[0], '</tr>\n')

os.write(t[0], '\n')
os.write(t[0], '</tbody></table>\n')

### COLLECTED PROFILE RESULTS ###

"""
os.write(t[0], '<h1>Function order dump</h1>')
os.write(t[0], '<table border="1"><thead><tr><th>Function</th><th>Function order</th></tr></thead><tbody>')

for item in gcc_dump_list:
  os.write(t[0], '<tr><td>' + item[0] + '</td><td>' + str(item[1]) + '</td></tr>')

os.write(t[0], '</tbody></table>')
"""

os.write(t[0], '</body></html>\n')

os.close(t[0])
print('HTML report file: file://' + t[1])
