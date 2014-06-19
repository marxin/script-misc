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
      return "%3.2f %s" % (num, x)
    num /= 1024.0

def parse_section_name(line):
  s = line.find(']') + 2
  e = line.find(' ', s)
  return line[s:e]

def parse_size(line):
  return int(line.split(' ')[0], 16)

if len(sys.argv) < 2:
  print('usage: readelf_sections <executable> [format_name={latex|csv}] <stap_file>')
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

stap_matches = len(sections) * [0]

if len(sys.argv) == 4:
  offsets = [int(x.strip().split(' ')[-1]) for x in open(sys.argv[3], 'r').readlines()]

  for i in offsets:
    for index, s in enumerate(sections):
      if s[1] <= i and i < s[1] + s[2]:
        stap_matches[index] += 4096
        break

if len(sys.argv) >= 3 and (sys.argv[2] == 'latex' or sys.argv[2] == 'csv'):
  if sys.argv[2] == 'latex':
    print('\hline')
    print('Section name & Size & Portion & Disk read & DR portion \\\\ \hline')

    threshold = 0.01 # 1%

    for index, s in enumerate(sections):
      stap = stap_matches[index]
      section_portion = 0.0
      if s[2] > 0:
        section_portion = 1.0 * stap / s[2] * 100

      if 1.0 * s[2] / total >= threshold:
        print_escaped(s[0] + ' & ' + str(sizeof_fmt(s[2])) + ' & ' + str("%0.2f %%" % (float(s[2]) / total * 100)) + ' & ' + sizeof_fmt(stap) + ' & ' + '%2.2f%%' % section_portion + ' \\\\ \hline')

    print_escaped('\\hline')
    print_escaped('Total & & ' + sizeof_fmt(total) + ' & ' + sizeof_fmt(sum(stap_matches)) + ' & ' + '%0.2f%%' % (100.0 * sum(stap_matches) / total) + '\\\\ \\hline')
  elif sys.argv[2] == 'csv':
    for s in sections:
      print(s[0] + ':' + str(s[1]) + ':' + str(s[2]) + ':' + str(sizeof_fmt(s[2])) + ':' + str("%0.2f" % (float(s[2]) / total * 100)))
else:
  print('%-20s%12s%12s%16s%11s%15s%12s%15s' % ('Section name', 'Start', 'Size in B', 'Size', 'Portion', 'Disk read in B', 'Disk read', 'Sec. portion'))
  for index, s in enumerate(sections):
    stap = stap_matches[index]

    section_portion = 0.0
    if s[2] > 0:
      section_portion = min(1.0 * stap / s[2] * 100, 100)
    print('%-20s%12s%12s%16s%10s%%%15u%12s%14s%%' % (s[0], str(s[1]), str(s[2]), sizeof_fmt(s[2]), str("%0.2f" % (float(s[2]) / total * 100)), stap, sizeof_fmt(stap), str("%0.2f" % section_portion)))

  stap_sum = sum(stap_matches)
  print('%44s%16s%26u%12s%14.2f%%' % (str(total), sizeof_fmt(total), stap_sum, sizeof_fmt(stap_sum), 100.0 * stap_sum / total))

