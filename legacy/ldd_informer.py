#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import shutil

def sizeof_fmt(num):
  for x in ['B','KB','MB','GB','TB']:
    if num < 1024.0:
      return "%3.1f %s" % (num, x)
    num /= 1024.0

if len(sys.argv) < 2:
  print('usage: ldd_informer <executable> [destination_copy_folder]')
  exit(-1)

target = sys.argv[1]
target_base = os.path.basename(target)

f = os.popen('LD_LIBRARY_PATH=./ ldd ' + target)

binsize = os.path.getsize(target)
print('%-32s%10s' % (target_base, str(sizeof_fmt(binsize))))

libraries = []
locations = [target]
total = 0

for line in f.readlines():
  line = line.strip()
  tokens = line.split(' ')
 
  if len(tokens) == 4:
    path = tokens[2]
    locations.append(path)
    size = os.path.getsize(path)
    total += size
    libraries.append([tokens[0], size])
  else:
    libraries.append([tokens[0], 0])

for l in sorted(libraries, key = lambda x: x[1], reverse = True):
    print('%-32s%10s' % (l[0], str(sizeof_fmt(l[1]))))

print('\nTOTAL')
print('Libraries: %31s' % sizeof_fmt(total))
print('Number of libs: %26s' % len(libraries))
print('Average library size: %20s' % (sizeof_fmt(total / len(libraries))))
print('Grand total: %29s' % sizeof_fmt(total + binsize))

# libraries copy process
if len(sys.argv) == 3:
  target_folder = sys.argv[2]

  if not os.path.exists(target_folder):
    os.mkdir(target_folder)

  for library in locations:
    print('Copying: %s -> %s' % (library, target_folder))
    shutil.copy(library, target_folder)
