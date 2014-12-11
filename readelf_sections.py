#!/usr/bin/env python

from __future__ import print_function

import os
import sys

def parse_section_name(line):
  s = line.find(']') + 2
  e = line.find(' ', s)
  return line[s:e]

def parse_size(line):
  return int(line.split(' ')[0], 16)

def sizeof_fmt(num):
  for x in ['B','KB','MB','GB','TB']:
    if num < 1024.0:
      return "%3.2f %s" % (num, x)
    num /= 1024.0

def to_percent(portion):
  return str('%.2f %%' % portion)

class ElfSection:
  def __init__ (self, section, offset, size):
    self.section = section
    self.offset = offset
    self.size = size

class ElfContainer:
  def __init__ (self, full_path):
    self.sections = []

    f = os.popen('readelf -S ' + full_path)

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
      self.sections.append(ElfSection(name, offset, size))

      i += 1

    self.total_size = sum(map(lambda x: x.size, self.sections))
    self.sections.append(ElfSection('TOTAL', 0, self.total_size))

  @staticmethod
  def print_containers (containers):
    first = containers[0]

    print('%-20s%12s%12s%12s%12s%12s' % ('section', 'portion', 'size', 'size', 'compared', 'comparison'))
    for s in first.sections:
      print ('%-20s%12s%12s%12s' % (s.section, to_percent(100.0 * s.size / first.total_size), sizeof_fmt(s.size), str(s.size)), end = '')

      for rest in containers[1:]:
	ss = [x for x in rest.sections if x.section == s.section][0]
	print('%12s' % str(ss.size), end = '')
	portion  = 100
	if ss.size > 0:
	  portion = 100.0 * ss.size / s.size
	print('%12s' % to_percent(portion), end = '')

      print()

if len(sys.argv) < 2:
  print('usage: readelf_sections <executables>')
  exit(-1)

containers = map(lambda x: ElfContainer(x), sys.argv[1:])
ElfContainer.print_containers(containers)
