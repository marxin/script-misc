#!/usr/bin/env python

from __future__ import print_function

import os
import sys

f = os.popen('readelf --wide -s ' + sys.argv[1])

array = []

for line in f.readlines():
  items = [x for x in line.strip().split(' ') if x] + [line.strip()]

  if len(items) > 5 and items[0][-1] is ':' and items[0][:-1].isdigit():
    array.append(items)

s = sorted(array, key = lambda x: int(x[1], 16))

for i in s:
  line = i[-1]
  s = line.find(' ')
  print(line[s:])
  # print(i[-2])
