#!/usr/bin/env python

from __future__ import print_function
from sets import Set

import os
import sys

if len(sys.argv) < 2:
  print('usage: path_to_elf [function_file]')

seen_functions = {}

if len(sys.argv) == 3:
  for func in open(sys.argv[2], 'r'):

    if func.startswith('.text.'):
      func = func[len('.text.'):]

    seen_functions[func.strip()] = True

# print(seen_functions)

f = os.popen('readelf --wide -s ' + sys.argv[1])

array = []

for line in f.readlines():
  items = [x for x in line.strip().split(' ') if x] + [line.strip()]

  if len(items) > 5 and items[0][-1] is ':' and items[0][:-1].isdigit() and items[2] != '0' and items[3] == 'FUNC':
    array.append(items)

s = sorted(array, key = lambda x: int(x[1], 16))

for i in s:
  line = i[-1]  
  s = line.find(' ')
  print(line[s:], end = '')
  
  funcname = i[7]
  i = funcname.find('@@')

  if i != -1:
    funcname = funcname[0:i]

  if funcname in seen_functions:
    print(' [SEEN]')
  else:
    print()

  # print(i[-2])
