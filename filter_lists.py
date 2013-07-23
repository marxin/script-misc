#!/usr/bin/env python

from __future__ import print_function

import os
import sys
from sets import Set

prefix = 'INIT:'

if len(sys.argv) != 3:
  print('usage: input_file filter_file')
  exit(-1)

items = [x.strip() for x in open(sys.argv[2], 'r').readlines()]

filter_items = Set(items)

for line in open(sys.argv[1], 'r'):
  line = line.strip()
  
  if line.startswith(prefix):
    line = line[len(prefix):]

  if line in filter_items:
    print(line)
