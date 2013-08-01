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
      lines = os.popen('/ssd/gcc2/objdir/gcc/gcov-dump -l ' + absolute).readlines()

      tp = False

#      print('scanning: ' + absolute)
      for l in lines:
        l = l.strip()
        if tp:
          if l.find(' 0 ') == -1:
            tokens = l.split(' ')
            total += 1
            count = int(tokens[-1])
            first = int(tokens[-3])
            f = first / count

            print(str(f) + ':' + absolute + ':' +  'total_first=' + str(first) +  ':' + 'total_count=' + str(count))

          tp = False
        elif l.find('time_profile') > 0:
          tp = True

print('TOTAL:' + str(total))
