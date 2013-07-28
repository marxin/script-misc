#!/usr/bin/env python

import os
import sys
import matplotlib.patches
import matplotlib.pyplot as plt
import matplotlib.collections as collections
from matplotlib.ticker import FuncFormatter
from itertools import *
import numpy as np

font_size = 38

plt.rc('text', usetex = True)
font = {'family' : 'serif', 'size' : font_size}
plt.rc('font',**font)
plt.rc('legend',**{'fontsize' : 0.8 * font_size})

alpha = 0.5

if len(sys.argv) < 3:
  print('usage: readpage_graph.py [data] [elf_executable] <graph_file>')
  exit(-1)

graph_sections = (('.text', '#5599ff'), ('.rel.dyn', 'r'), ('.rela.dyn', '#e9afaf'), ('.data.rel.ro', 'y'), ('.eh_frame', '#de87de'), ('.eh_frame_hdr', '#de87de'), ('.rodata', 'c'), ('.dynstr', '#ffa500'), ('.symtab', '#666f00'), ('.strtab', '#006f66'), ('.init_array', '#000000'))

def parse_section_name(line):
  s = line.find(']') + 2
  e = line.find(' ', s)
  return line[s:e]

def parse_size(line):
  return int(line.split(' ')[0], 16)

def parse_readelf(target):
  f = os.popen('readelf -S ' + target)

  lines = f.readlines()[5:-4]

  i = 0
  total = 0
  sections = []

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

  return sections

f = open(sys.argv[1], 'r')

k = 2
fig = plt.figure(figsize = (k * 18, k * 10))
ax = fig.add_subplot(111)
xs = []
ys = []

start = 0
for line in f:
  columns = line.split(' ')
  if start == 0:
    start = int(columns[0])

  xs.append(int(columns[0]) - start)
  ys.append(int(columns[2].strip()))

sections = filter(lambda x: x[0] in map(lambda x: x[0], graph_sections),  parse_readelf(sys.argv[2]))

maxx = max(xs)
legends = [[], []]

for s in sections:
  item = next(ifilter(lambda x: x[0] == s[0], graph_sections), None)
  c = collections.BrokenBarHCollection([(0, maxx)], (s[1], s[2]), facecolor = item[1], edgecolor = 'white', alpha = alpha)
  ax.add_collection(c)
  legends[0].insert(0, matplotlib.patches.Rectangle((0, 0), 1, 1, fc = item[1], alpha = alpha))
  legends[1].insert(0, s[0].replace('_', '\_'))

ax.plot(xs, ys, color='black', marker='o', markerfacecolor='r', mec = 'r', mew = 0, markersize = 2, linewidth = 0.1, linestyle = '-')
ax.set_xlim(0, maxx)
ax.legend(legends[0], legends[1], loc = 9)

ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: ('%d') % (x / (1023 * 1024))))
ax.set_ylabel('Offset (MB)')

ax.xaxis.set_major_formatter(FuncFormatter(lambda y, pos: ('%d') % (y / 1000)))
ax.set_xlabel('Time (ms)')

if len(sys.argv) >= 4:
  plt.tight_layout()
  fig.savefig(sys.argv[3])
else:
  fig.show()
