#!/usr/bin/env python

from __future__ import print_function
from os import listdir

import os
import sys
import fnmatch
import datetime

timestamp = datetime.datetime(2013, 4, 15, 0, 0, 0)

lib_folders=['/lib64', '/usr/lib64']
bin_folders= os.environ['PATH'].split(':')

def is_elf(filename):
  l = os.popen('file ' + filename).readlines()
  iself = l[0].find('ELF 64') != -1
  return iself

def sizeof_fmt(num):
  for x in ['bytes','KB','MB','GB','TB']:
    if num < 1024.0:
      return "%3.1f %s" % (num, x)
    num /= 1024.0

def get_files(folder):
  files = set()

  for i in listdir(folder):
    filename = os.path.join(folder, i)
    if not os.path.isfile(filename):
      continue
    if os.path.islink(filename):
      files.add(os.path.realpath(filename))
    else:
      files.add(filename)

  return files

def build_summary(folders):
  s = set()

  for folder in folders:
    s = s.union(get_files(folder))

  return [(x, datetime.datetime.fromtimestamp(os.path.getmtime(x)), os.stat(x).st_size) for x in s if is_elf(x)]


candidates = [build_summary(bin_folders), build_summary(lib_folders)]

if len(sys.argv) == 2:
  tuples = [(x.strip().split(':')[0], x.strip().split(':')[1]) for x in open(sys.argv[1]).readlines() if not x.strip().startswith('#')]
  dictionary = dict(tuples)

  for i in candidates:
    younger = [x for x in i if x[1] > timestamp]

    sum_old = 0
    sum_new = 0
    for file in younger:
      n = file[0]
      len_old = int(file[2])
      len_new = int(dictionary[n])

      sum_old += len_old
      sum_new += len_new

      print('%s:%u:%u:%f' % (n, len_old, len_new, 100.0 * len_new / len_old))

    print('DIFF: %s:%s:%f' % (sizeof_fmt(sum_old), sizeof_fmt(sum_new), 100.0 * sum_new / sum_old))

else:
  for i in candidates:
    all = len(i)
    younger = [x for x in i if x[1] > timestamp]
    good = len(younger)

    print('# HAVING: %u/%u' % (good, all))
    for file in younger:
      print('%s:%u' % (file[0], file[2]))
