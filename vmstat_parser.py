#!/usr/bin/env python

from __future__ import print_function
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from psutil import virtual_memory

import os
import sys
import getopt

cores = 8
colors = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']
total_memory = virtual_memory().total / (1024 * 1024 * 1024)

class DataLine:
  def __init__(self, name):
    self.name = name
    self.x = []
    self.y = []

  def __eq__(self, other):
    return self.name == other.name

  def add(self, time, value):
    self.x.append(time)
    self.y.append(value)

  def shift_x(self, c):
    self.x = [x - c for x in self.x]

  def shift_y(self, c):
    self.y = [y - c for y in self.y]

  def scale(self, c):
    self.y = [1.0 * y / c for y in self.y]

  def unify_y(self, max):
    d = {}

    for i, v in enumerate(self.x):
      d[int(round(v))] = self.y[i]

    a = [0] * (max + 1)
    for i, v in enumerate(a):
      if i in d:
	a[i] = d[i]

    self.y = a

    # value interpolation
    for i, v in enumerate(self.y[:-1]):
      if v == 0:
	prev_values = filter(lambda x: x > 0, self.y[:i])
        next_values = filter(lambda x: x > 0, self.y[i:])

	if len(next_values) > 0 and len(prev_values) > 0:
	  self.y[i] = prev_values[-1]

  def max_x(self):
    return max(self.x)

  def min_x(self):
    return min(self.x)

  def min_y(self):
    return min(self.y)

def parse_file(filename):
  f = open(filename)

  datalines = {}

  for line in f:
    tokens = line.strip().split(':')
    name = tokens[0]

    d = None
    if name in datalines:
      d = datalines[name]
    else:
      d = DataLine(name)
      datalines[name] = d

    d.add(float(tokens[1]), float(tokens[2]))

  min_time = min(map(lambda x: x.min_x(), datalines.values()))

  # time shift
  for item in datalines.values():
    item.shift_x(min_time)

  # ram shift
  ram = datalines['RAM']
  cpu = datalines['CPU']

  min_ram = ram.min_y()
  ram.shift_y(min_ram)

  #scale
  for v in datalines.values():
    if v != cpu:
      v.scale(1024 * 1024)

  return datalines

def unify_data(datalines, global_max_time):
  for item in datalines.values():
    item.unify_y(global_max_time)

def write_to_subplot(path, datalines, cpu_subplot, ram_subplot, global_max_time):
  # TODO
  ram = datalines['RAM']
  cpu = datalines['CPU']

  ram_peak = max(ram.y)

  sorted_stack = [datalines[x] for x in sorted(datalines.keys()) if x != 'CPU' and x != 'RAM']
  stack_x = range(0, global_max_time + 1)
  stack_y = [x.y for x in sorted_stack]

  title_prefix = os.path.basename(path).upper().replace('_', '\_')

  cpu_subplot.plot(cpu.y)
  cpu_subplot.set_title(title_prefix + '@CPU (red=single core)')
  cpu_subplot.set_ylabel('\%')
  cpu_subplot.set_xlim([0, global_max_time])
  cpu_subplot.set_ylim([0, 105])
  cpu_subplot.axhline(linewidth = 1, color = 'r', y = 100.0 / cores)

  ram_subplot.plot(ram.y, c = 'blue', lw = 2)
  ram_subplot.set_title(title_prefix + '@RAM (peak: %2.2f GB)' % (ram_peak))
  ram_subplot.set_ylabel('GB')
  ram_subplot.set_ylim([0, total_memory])

  yticks = range(total_memory) if total_memory <= 8 else np.arange(0, total_memory, 2)
  ram_subplot.set_yticks(yticks)

  ram_subplot.stackplot(stack_x, stack_y, colors = colors)

def main():
  optlist, args = getopt.getopt(sys.argv[1:], 'o:m:')

  if len(args) == 0:
    print('usage: vmstat_parser {data_files} -o pdf_file')
    exit(-1)

  output_file = None

  for o, a in optlist:
    if o == '-o':
      output_file = a
    elif o == '-m':
      global total_memory
      total_memory = int(a)
    else:
      assert False, "Unhandled option"

  total_memory = 8
  # TODO: fix me
  output_file = args[-1]
  args = args[:-1]

  plt.rc('text', usetex = True)
  font = {'family' : 'serif', 'size':13}
  plt.rc('font',**font)
  plt.rc('legend',**{'fontsize':11})

  file_names = args 

  axarr = None

  # data parsing
  file_datas = []

  for i in file_names:
    file_datas.append(parse_file(i))

  global_max_time = int(round(max(map(lambda f: max(map(lambda x: x.max_x(), f.values())), file_datas))) + 10)

  for i in file_datas:
    unify_data(i, global_max_time)

  # DATA PRESENTATION
  plt.rcParams['figure.figsize'] = 20, (5 * len(file_datas))

  if len(file_names) == 1:
    plt.rcParams['figure.figsize'] = 10, 5
    f, axarr = plt.subplots(2, sharex = True)
    write_to_subplot(file_names[0], file_datas[0], axarr[0], axarr[1], global_max_time)
    axarr[0].grid(True)
    axarr[1].grid(True)
  else:
    f, axarr = plt.subplots(len(file_names), 2, sharex = True)

    for i, v in enumerate(file_names):
      write_to_subplot(v, file_datas[i], axarr[i, 0], axarr[i, 1], global_max_time)
      for j in range(0, 2):
	axarr[i, j].set_xlabel('time (s)')
	axarr[i, j].grid(True)

  plt.tight_layout(pad = 0.5, w_pad = 0.5, h_pad = 0.5)

  if output_file != None:
    plt.savefig(output_file)
  else:
    plt.show()

### MAIN ###
main()
