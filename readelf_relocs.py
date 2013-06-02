#!/usr/bin/env python

from __future__ import print_function

import os
import sys

if len(sys.argv) < 2:
  print('usage: readelf_relocs <executable>')
  exit(-1)

f = os.popen('readelf -W -r ' + sys.argv[1])

dict = {}

section = ''

for l in f.readlines():
  items = [x for x in l.split(' ') if x]

  if l.startswith('Relocation section'):
    section = items[2][1:][:-1]
    dict[section] = {}

  if l[0] != '0':
    continue

  type = items[2]
  if type in dict[section]:
    dict[section][type] += 1
  else:
    dict[section][type] = 1

statistics = []

for section in dict:
  for k,v in dict[section].items():
    statistics.append([k, v, section])

sorted_stats = sorted(sorted(statistics, key = lambda x: x[1]), key = lambda x: x[2])

total = 0

for i in sorted_stats:
  print('%-24s%24s%12s%12s' % (i[0], i[1], i[2], str(i[1] * 24)))
  total += i[1]  

print('%48s%24s' % (total, str(total * 24)))
