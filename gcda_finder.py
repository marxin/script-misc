#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import fnmatch

if len(sys.argv) != 2:
  exit(-1)

p = sys.argv[1]

"""
commands = []

for root, dirnames, filenames in os.walk(p):
    for filename in fnmatch.filter(filenames, '*.gcda'):
      absolute = os.path.join(root, filename)
      commands.append('/ssd/gcc2/objdir/gcc/gcov-dump -l ' + absolute)

for c in commands:
  print(c)

"""

lines = open(p, 'r').readlines()

tp = False

for l in lines:
  l = l.strip()
  if tp:
    if l.find(' 0 ') == -1:
      print(l)

    tp = False
  elif l.find('time_profile') > 0:
    tp = True
