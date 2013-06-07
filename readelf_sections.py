#!/usr/bin/env python

from __future__ import print_function

import os
import sys

sections = []

def print_escaped(line):
  line = line.replace('_', '\_')
  line = line.replace('%', '\%')
  print(line)

def sizeof_fmt(num):
  for x in ['B','KB','MB','GB','TB']:
    if num < 1024.0:
      return "%3.1f %s" % (num, x)
    num /= 1024.0

def parse_section_name(line):
  s = line.find(']') + 2
  e = line.find(' ', s)
  return line[s:e]

def parse_size(line):
  return int(line.split(' ')[0], 16)

if len(sys.argv) < 2:
  print('usage: readelf_sections <executable> [format_name={latex|csv}]')
  exit(-1)

target = sys.argv[1]

f = os.popen('readelf -S ' + target)

lines = f.readlines()[5:-4]

i = 0
total = 0

while i < len(lines):
  line = lines[i].strip()
  name = parse_section_name(line)
  offset = int(line.split(' ')[-1], 16)

  i += 1

  line = lines[i].strip()
  size = parse_size(line)
  sections.append((name, offset, size))
  total += size

  i += 1

if len(sys.argv) == 3:
  if sys.argv[2] == 'latex':
    print('\hline')
    print('section & offset (in B) & offset & size (in B) & size & portion \\\\ \hline')

    for s in sections:
      print_escaped(s[0] + '&' + str(s[1]) + '&' + sizeof_fmt(s[1]) + '&' + str(s[2]) + '&' + str(sizeof_fmt(s[2])) + '&' + str("%0.2f %%" % (float(s[2]) / total * 100)) + ' \\\\ \hline')
  elif sys.argv[2] == 'csv':
    for s in sections:
      print(s[0] + ':' + str(s[1]) + ':' + str(s[2]) + '&' + str(sizeof_fmt(s[2])) + ':' + str("%0.2f" % (float(s[2]) / total * 100)))
else:
  print('%-20s%12s%12s%16s%10s' % ('Section name', 'Start', 'Size in B', 'Size', 'Portion'))
  for s in sections:
    print('%-20s%12s%12s%16s%10s%%' % (s[0], str(s[1]), str(s[2]), sizeof_fmt(s[2]), str("%0.2f" % (float(s[2]) / total * 100))))
  print('%44s%16s' % (str(total), sizeof_fmt(total)))

