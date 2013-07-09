#!/usr/bin/env python

from __future__ import print_function
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import os
import sys

# TODO: font folder correction
# plt.rc('font', family='serif') 
# plt.rc('font', serif='MU Classical Serif')

cores = 8

if len(sys.argv) < 2:
  print('usage: vmstat_parser [data_file] {pdf_file}')
  exit(-1)

f = open(sys.argv[1])

memory = []
cpu = []

for line in f:
  line = line.strip()

  if not line[0].isdigit():
    continue

  tokens = [x for x in line.split(' ') if x]

  memory.append(int(tokens[5]))
  cpu_usage = min(100, int(tokens[12]) + int(tokens[13]))
  cpu.append(cpu_usage)

memory_min = min(memory)
memory = [1.0 * (x - memory_min) / (1024 * 1024) for x in memory]

# DATA PRESENTATION
plt.rcParams['figure.figsize'] = 10, 6
f, axarr = plt.subplots(2, sharex = True)

axarr[0].plot(cpu)
axarr[0].set_title('CPU utilization')
axarr[0].set_ylabel('%')
axarr[0].grid(True)
axarr[0].set_xlim([0, len(memory) + 10])
axarr[0].set_ylim([0, 105])
axarr[0].axhline(linewidth = 2, color = 'r', y = 100.0 / cores)

axarr[1].plot(memory)
axarr[1].set_title('memory usage')
axarr[1].set_xlabel('time (s)')
axarr[1].set_ylabel('RAM (in GB)')
axarr[1].grid(True)

if len(sys.argv) >= 3:
  location = sys.argv[2]
  plt.savefig(location)

else:
  plt.show()
