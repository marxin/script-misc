#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import fnmatch

if len(sys.argv) != 2:
  exit(-1)

p = sys.argv[1]

total = 0

for root, dirnames, filenames in os.walk(p):
    for filename in fnmatch.filter(filenames, '*.gcda'):
      absolute = os.path.join(root, filename)
      lines = os.popen('/ssd/gcc/objdir/gcc/gcov-dump -l ' + absolute).readlines()

      tp = False

      for l in lines:
        l = l.strip()
        if tp:
          if l.find('0 0') == -1:
            # print(l)
            tokens = l.split(' ')
            total += 1
            first = int(tokens[-1])

            print(absolute + ':' + str(first))

          tp = False
        elif l.find('time_profile') > 0:
          tp = True

print()
print('TOTAL:' + str(total))
