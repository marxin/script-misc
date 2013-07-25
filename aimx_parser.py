#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import re

if len(sys.argv) <= 1:
  print('usage: aimx_parser [data_files]')
  exit(-1)

files = sys.argv[1:]

file_names = []
results = []

# parsing
for f in files:
  lines = [x for x in open(f, 'r').readlines() if re.match('^\ +[0-9]+\ ', x)]
  n = os.path.basename(f)
  file_names.append(n)
  results.append([])
  
  for line in lines:
    score = [x for x in line.strip().split(' ') if x][5]
    results[-1].append(float(score))

# comparison
for idx, test in enumerate(files):
  basetest = results[0]

  score = 0
  for i, v in enumerate(basetest):
    diff = 1.0 * results[idx][i] / v
    # print(diff)
    score += diff

  score /= len(basetest)
  print('%s: %.2f%%' % (test, 100 * score))
