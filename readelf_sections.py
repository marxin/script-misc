#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
from collections import defaultdict
from itertools import groupby

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

def to_percent(a, b):
  if b == 0:
    return '0 %'

  return str('%.2f %%' % (100.0 * a / b))

class ElfSymbol:
  def __init__ (self, name, type, attribute):
    self.name = name
    self.type = type
    self.attribute = attribute

  def __eq__(self, obj):
    return self.name == obj.name and self.type == obj.type and self.attribute == obj.attribute

  def __hash__(self):
     return hash(self.name + self.type + self.attribute)

  def __str__(self):
    return 'name: %s, type: %s, attr: %s' % (self.name, self.type, self.attribute)

  def group(self):
    return self.type + '_' + self.attribute

class ElfSection:
  def __init__ (self, section, offset, size):
    self.section = section
    self.offset = offset
    self.size = size

class ElfContainer:
  def __init__ (self, full_path):
    self.parse_sections(full_path)
    self.parse_symbols(full_path)

    sorted_input = sorted(self.symbols, key = lambda x: x.group())
    self.symbols_dictionary = {}

    for k, g in groupby(sorted_input, key = lambda x: x.group()):
      self.symbols_dictionary[k] = list(g)

  def parse_sections (self, full_path):
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

  def parse_symbols (self, full_path):
    f = os.popen('readelf --wide -s ' + full_path)
    self.symbols = []

    for line in f.readlines():
      items = [x for x in line.strip().split(' ') if x]
      if len(items) == 8 and items[1][-1].isdigit():
        name = items[7]
        type = items[3]
        attribute = items[4]
        self.symbols.append(ElfSymbol(name, type, attribute))

  def compare_symbols (self, compared):
    print('Symbol count comparison')
    all_keys = set(self.symbols_dictionary.keys ()).union(set(compared.symbols_dictionary.keys()))
    fmt = '%-20s%12s%12s%12s'

    sums = [0, 0]

    for k in all_keys:
      v = []
      v2 = []

      if k in self.symbols_dictionary:
        v = self.symbols_dictionary[k]
        sums[0] = sums[0] + len(v)
      if k in compared.symbols_dictionary:
        v2 = compared.symbols_dictionary[k]
        sums[1] = sums[1] + len(v)

      print(fmt % (k, len(v), len(v2), to_percent(len(v2), len(v))))

    print(fmt % ('TOTAL', str(sums[0]), str(sums[1]), to_percent(sums[1], sums[0])))
    print()

  """
      lf = set(self.symbols_dictionary['FUNC_LOCAL'])
      compared_lf = set(compared.symbols_dictionary['FUNC_LOCAL'])

      for i in lf - compared_lf:
	print('Just in GCC: %s' % i)

      for i in compared_lf - lf:
	print('Just in CLANG: %s' % i)
  """


  @staticmethod
  def print_containers (containers):
    first = containers[0]

    print('%-20s%12s%12s%12s%12s%12s' % ('section', 'portion', 'size', 'size', 'compared', 'comparison'))
    for s in first.sections:
      print ('%-20s%12s%12s%12s' % (s.section, to_percent(s.size, first.total_size), sizeof_fmt(s.size), str(s.size)), end = '')

      for rest in containers[1:]:
        ss = [x for x in rest.sections if x.section == s.section][0]
        print('%12s' % str(ss.size), end = '')
        portion = to_percent (ss.size, s.size)
        print('%12s' % portion, end = '')

      print()

if len(sys.argv) < 2:
  print('usage: readelf_sections <executables>')
  exit(-1)

containers = list(map(lambda x: ElfContainer(x), sys.argv[1:]))

containers[0].compare_symbols(containers[1])

ElfContainer.print_containers(containers)
