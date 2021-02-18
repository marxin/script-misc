#!/usr/bin/env python

from __future__ import print_function
from os import listdir
from termcolor import colored

import os
import sys
import fnmatch
import datetime

timestamp = datetime.datetime(2014, 4, 18, 9, 36, 0)
ignores = ['python3.3', 'python2.7', 'gst-launch', 'llvm', 'bin/lli']

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
    if not os.path.exists(folder):
      continue

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
    lines = []
    for file in younger:
      n = file[0]

      if n.endswith('.a') or n.find('gcc-bin') >= 0 or any(map(lambda x: n.find(x) >= 0, ignores)):
        print('Skipping file: %s' % n)
        continue

      len_old = int(file[2])

      if n in dictionary:      
        len_new = int(dictionary[n])

        if len_old == len_new:
          print('Skipping same sizes: %s' % n)

        sum_old += len_old
        sum_new += len_new

        percent = 100.0 * len_new / len_old
        s = '%-80s%-10s%-10s%3.2f%%' % (n, len_old, len_new, percent)
        line = colored(s, 'red' if percent > 100 else ('cyan' if percent < 10 else 'green'))
        lines.append((percent, line))
      else:
        print('Missing item: %s' % (n))

    for line in sorted(lines, key = lambda x: x[0]):
      print(line[1])

    print(colored('SUMMARY%73s%-10s%-10s%3.2f%%' % ('', sizeof_fmt(sum_old), sizeof_fmt(sum_new), 100.0 * sum_new / sum_old), 'yellow'))

else:
  for i in candidates:
    all = len(i)
    younger = [x for x in i if x[1] > timestamp]
    older = [x for x in i if x[1] < timestamp]
    good = len(younger)

    print('# HAVING: %u/%u' % (good, all))
    for file in younger:
      print('%s:%u' % (file[0], file[2]))

    for file in older:
      print('# %s:%u:%s' % (file[0], file[2], file[1]))
