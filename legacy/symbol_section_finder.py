#!/usr/bin/env python

from __future__ import print_function

import os
import sys

if len(sys.argv) < 3:
  print('usage: symbol_section_finder [function_list_file] <object_file_array>')

def find_symbol(symbol):
  for f in seen_functions:
    if symbol in objects:
      return (objects[symbol],symbol)

  return None

def find_nth(s, pattern, n):
  index = 0

  for i in range(0,n):
    r = s[index:].find(pattern)
    if r == -1:
      return -1
    else:
      index += r + 1

  return index

def find_symbol_wrapper(symbol):
  original = symbol

  prefixes = ['', 'startup.', 'unlikely.', 'hot.']

  for i in prefixes:
    r = find_symbol('.text.' + i + symbol)

    if r != None:
      return r

  symbol = '.text.' + symbol

  # unknown pattern
  newsymbol = symbol.replace('C1', 'C2')
  r = find_symbol(newsymbol)

  if r != None:
    return r

  newsymbol = symbol.replace('D1', 'D2')
  r = find_symbol(newsymbol)

  if r != None:
    return r

  # thunk handling
  if original.startswith('_ZTv0_'):
    newsymbol = '.text._Z' + original[find_nth(original, '_', 3):]

  r = find_symbol(newsymbol)

  if r != None:
    return r

  if original.startswith('_ZThn'):
    newsymbol = '.text._Z' + original[find_nth(original, '_', 2):]

  r = find_symbol(newsymbol)

  if r != None:
    return r

  return None

# function list creation
seen_functions = []

for func in open(sys.argv[1], 'r'):

  if func.startswith('.text.'):
    func = func[len('.text.'):]

  seen_functions.append(func.strip())

# object files parsing
objects = {}
files = []

if sys.argv[2] == '--combine':
  for f in open(sys.argv[3], 'r'):
    i = f.find('"') + 1
    files.append(f[i:-3]) 


  files += sys.argv[4:]
  print(len(files))
else:
  files = sys.argv[2:]

for objname in files:
  print('Parsing object file: ' + objname, end = '')
  if not os.path.isfile(objname):
    print(' file not found')
    continue

  f = os.popen('readelf --wide -S ' + objname + ' | grep \' .text\\.\'')
  count = 0

  for line in f.readlines():
    section = [x for x in line[line.index(']'):].split(' ') if x][1]
    objects[section] = objname
    count += 1

  print(' (%u)' % count)

found = 0
missing = 0

print('Sections count: %u' % len(objects))
print('Total functions: %u' % len(seen_functions))
print('\nMissing symbols:')

result = []

for func in seen_functions:
  r = find_symbol_wrapper(func)

  if r == None:
    missing += 1

  if r != None:
    found += 1

  if r == None:
    print(func, file = sys.stderr)
    print(func + ' ' + str(r))
  else:
    print(r[1], file = sys.stderr)

print()
print('Found: ' + str(found))
print('Missing: ' + str(missing))
