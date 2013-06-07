#!/usr/bin/env python

from __future__ import print_function

import os
import sys

def sizeof_fmt(num):
  for x in ['bytes','KB','MB','GB','TB']:
    if num < 1024.0:
      return "%3.1f %s" % (num, x)
    num /= 1024.0

if len(sys.argv) != 2:
  print('usage: ldd_informer <executable>')
  exit(-1)

target = sys.argv[1]
target_base = os.path.basename(target)

f = os.popen('ldd ' + target)

size = os.path.getsize(target)
print(target_base + ' (' + str(sizeof_fmt(size)) + ')')

for line in f.readlines():
  line = line.strip()
  tokens = line.split(' ')
 
  print('\t' + tokens[0], end = '')
  if len(tokens) == 4:
    path = tokens[2]
    size = os.path.getsize(path)
    print('(' + str(sizeof_fmt(size)) + ')')
  else:
    print()
