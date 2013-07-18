#!/usr/bin/env python

from __future__ import print_function

from pylab import *
import numpy as np
import matplotlib.pyplot as plt

import os
import sys

plt.rc('text', usetex = True)
font = {'family' : 'serif', 'size':13}
plt.rc('font',**font)
plt.rc('legend',**{'fontsize':11})

if len(sys.argv) != 2:  
  print('usage: spec_statistics data_folder')
  exit(1)

datafolder = sys.argv[1]

base_profile = 'gcc48-O2'
data = [{}, {}]

int_benchmarks = [400, 401, 403, 429, 445, 456, 458, 462, 464, 471, 473, 483]

profile_order = [
                  'gcc48-O2',
                  'gcc48-O3',
                  'gcc49-O2',
                  'gcc49-O3',
                  'gcc49-O2-LTO',
                  'gcc49-O3-LTO',
                  'gcc49-O3-LTO-UG5',
                  'gcc49-O3-PGO',
                  'gcc49-O3-LTO-PGO',
                  'gcc49-O2-LIPO',
                  'gcc49-O3-LIPO',
                  'gcc49-O3-LTO1',
                  'gcc49-O3-LTO1-SE'
                ]

def sort_profiles(names):
  return sorted(names, key = lambda x: profile_order.index(x))

def is_int(name):
  n = int(name.split('.')[0])
  return n in int_benchmarks

is_fp = lambda x: not is_int(x)

def parse_file(path, t):
  f = open(os.path.join(datafolder, path), 'r')
  d = {}

  for line in f:
    tokens = line.strip().split(':')
    d[tokens[0]] = [t(tokens[1])]

  return d

# MAIN
for filename in os.listdir(datafolder):
  filename = filename.strip()
  if filename.endswith('-time.csv'):
    profile = filename[:filename.rfind('-')]
    data[0][profile] = {}
    data[0][profile] = parse_file(filename, float)

  if filename.endswith('-size.csv'):
    profile = filename[:filename.rfind('-')]
    data[1][profile] = {}
    data[1][profile] = parse_file(filename, float)

def average(profile, selector):
  data = map(lambda x: profile[x][1], filter(selector, profile.keys()))
  return sum(data) / len(data)

def aggregate(datasource, aggregate, selector = lambda x: True):
  r = {}

  for p in datasource.keys():
    profile = datasource[p]    

    if aggregate:
      r[p] = average(profile, selector)
    else:
      r[p] = {}
      for k in filter(selector, profile.keys()):
        r[p][k] = profile[k][1]

  return r

def transform_summary(aggregates, labels):
  d = {}

  for idx, label in enumerate(labels):
    d[label] = aggregates[idx]

  return d

def transform_to_table(d, header_sorter = lambda x: sorted(x), row_sorter = lambda x: sorted(x)):
  header = ['']

  header_keys = header_sorter(d.keys())

  for k in header_keys:
    header.append(k)

  table = [header]

  third = row_sorter(d[d.keys()[0]])

  for t in third:
    line = [t]
    for k in header_keys:
      if t in d[k]:
        line.append(d[k][t])
      else:
        line.append(None)

    table.append(line)

  # average line
  average_line = ['average']
  for profile in header_keys:
    l = map(lambda x: d[profile][x], d[profile].keys())
    average_line.append(sum(l) / len(l))

  table.append(average_line)
  return table

def transform_to_latex(table, filt, column_header_filter = lambda x: x, caption = None, label = None, double_last = True):
  header = table[0]
  l = len(header)

  print('\\begin{table}')
  print('\t\\begin{tabular}{', end = '')

  format = ''
  for i in header:
    format += '|r'

  format += '|}'

  format = format.replace('r', 'l', 1)
  print(format)

  print('\t\hline')

  #header
  for column in header[:-1]:
    print('\\textbf{' + column_name_filter(column) + '} & ', end = '')

  print('\\textbf{' + column_header_filter(header[-1]) + '} \\\\ \\hline')

  iterate = table[1:-1]

  # body
  for line in iterate:
    for i, item in enumerate(line[:-1]):
      if i > 0:
        print(filt(item) + ' & ', end = '')
      else:
        print('\\textbf{' + filt(item) + '} & ', end = '')

    print(filt(line[-1]) + ' \\\\ \\hline')

  if double_last:
    print('\\hline')
    for column in table[-1][:-1]:
      print('\\textbf{' + filt(column) + '} & ', end = '')

    print('\\textbf{' + filt(table[-1][-1]) + '} \\\\ \\hline')


  print('\t\\end{tabular}')

  if caption != None:
    print('\t\\caption{' + caption + '}')
    
  if label != None:
    print('\t\\label{fix:' + label + '}')

  print('\\end{table}')

# aggregate phase
for i, d in enumerate(data):
  for p in d.keys():
    for b in d[p].keys():
      if i == 0:
        d[p][b].append(data[i][base_profile][b][0] / d[p][b][0] - 1)
      else:
        d[p][b].append(d[p][b][0] / data[i][base_profile][b][0] - 1)

def color_wrap(value, color):
  return '\cellcolor{%s}%s' % (color, value)

def time_percent_filter(x):
  return percent_filter(x, True)

def size_percent_filter(x):
  return percent_filter(x, False)

def simple_percent_filter(x):
  return percent_filter(x, False, False)

def percent_filter(x, reverse, color = True):
  if isinstance(x, float):
    s = '{0:.2%}'.format(x).replace('%', '\\%')

    if color:
      if reverse:
        if x > 0.1:
          return color_wrap(s, 'SpecBetter')
        elif x > 0.05:
          return color_wrap(s, 'SpecGood')
        elif x < -0.1:
          return color_wrap(s, 'SpecWorse')
        elif x < -0.05:
          return color_wrap(s, 'SpecBad')
        else:
          return s
      else:
        if x > 0.50:
          return color_wrap(s, 'SpecWorse')
        elif x > 0.25:
          return color_wrap(s, 'SpecBad')
        elif x < -0.50:
          return color_wrap(s, 'SpecBetter')
        elif x < -0.25:
          return color_wrap(s, 'SpecGood')
        else:
          return s
    else:
      return s

  if x == None:
    return 'N/A'

  return str(x)

def split_table(table):
  boundary = 6
  t1 = []
  t2 = []
  
  for line in table:
    t1.append(line[:(boundary + 1)])
    t2.append(line[:1] + line[(boundary + 1):])

  return (t1, t2)

def column_name_filter(name):
  if len(name) <= 3 or not name.startswith('gcc'):
    return name

  name = name[3:]

  if name.startswith('49'):
    name = name[3:]

  name = name.replace('LIPO', 'L')
  name = name.replace('PGO', 'P')

  return name

def generate_graph(data, label, filename):
  for k in data:
    data[k] = (data[k] + 1) * 100

  keys = sort_profiles(data.keys())
  values = [data[x] for x in keys]

  width = 0.7

  plt.rcParams['figure.figsize'] = 10, 6
  fig = plt.figure()
  ax = fig.add_subplot(111)

  ax.set_title(label)
  x = np.arange(len(keys)) + width / 2
  rects = ax.bar(x, values, width, color = 'y')
  xticks(x, keys)
  plt.xticks(rotation = 60)
  axhline(linewidth = 2, color = 'r', y = 100)
  ylabel('\%')

  grid(True)
  tight_layout(1.5)

  savefig(filename)
 

time_summary = [aggregate(data[0], True), aggregate(data[0], True, is_int), aggregate(data[0], True, is_fp)]
size_summary = [aggregate(data[1], True), aggregate(data[1], True, is_int), aggregate(data[1], True, is_fp)]

# 1) performance
all_performance_data = transform_summary(time_summary, ['Speedup', 'Speedup (INT)', 'Speedup (FP)'])
all_performance = transform_to_table(all_performance_data, row_sorter = sort_profiles)

# 2) size
all_size_data = transform_summary(size_summary, ['Size ', 'Size (INT)', 'Size (FP)'])
all_size = transform_to_table(all_size_data, row_sorter = sort_profiles)

# 3) performance for INT profiles and benchmarks
int_performance = transform_to_table(aggregate(data[0], False, is_int), sort_profiles)

# 4) performance for FP profiles and benchmarks
fp_performance = transform_to_table(aggregate(data[0], False, is_fp), sort_profiles)

# 5) size for INT profiles and benchmarks
int_size = transform_to_table(aggregate(data[1], False, is_int), sort_profiles)

# 6) size for FP profiles and benchmarks
fp_size = transform_to_table(aggregate(data[1], False, is_fp), sort_profiles)

# GRAPH creation
time_graph_data = aggregate(data[0], True)
size_graph_data = aggregate(data[1], True)

generate_graph(time_graph_data, 'SPEC CPU2006 - performance', '/tmp/spec-performance-graph.pdf')
generate_graph(size_graph_data, 'SPEC CPU2006 - binary size', '/tmp/spec-size-graph.pdf')

exit(0)

print(time_graph_data)

print('\n% 1) performance')

transform_to_latex(all_performance, simple_percent_filter, column_name_filter, 'SPEC CPU2006 speedup summary', 'Spec2006SpeedupSummary', False)
print()

print('\n% 2) size')
transform_to_latex(all_size, simple_percent_filter, column_name_filter, 'SPEC CPU2006 binary reduction', 'Spec2006BinarySizeReduction', False)

print()

print('\n% 3) int_performance')

transform_to_latex(split_table(int_performance)[0], time_percent_filter, column_name_filter, 'SPEC CPU2006 INT speedup, part I', 'Spec2006IntSpeedupPart1')
print()
transform_to_latex(split_table(int_performance)[1], time_percent_filter, column_name_filter, 'SPEC CPU2006 INT speedup, part II', 'Spec2006IntSpeedupPart2')
print()

print('\n% 4) fp_performance')
transform_to_latex(split_table(fp_performance)[0], time_percent_filter, column_name_filter, 'SPEC CPU2006 FP speedup, part I', 'Spec2006FpSpeedupPart1')
print()
transform_to_latex(split_table(fp_performance)[1], time_percent_filter, column_name_filter, 'SPEC CPU2006 FP speedup, part II', 'Spec2006FpSpeedupPart2')
print()

print('\n% 5) int_size')
transform_to_latex(split_table(int_size)[0], size_percent_filter, column_name_filter, 'SPEC CPU2006 INT size reduction, part I', 'Spec2006IntSizeReductionPart1')
print()
transform_to_latex(split_table(int_size)[1], size_percent_filter, column_name_filter, 'SPEC CPU2006 INT size reduction, part II', 'Spec2006IntSizeReductionPart2')

print('\n% 6) fp_size')
transform_to_latex(split_table(fp_size)[0], size_percent_filter, column_name_filter, 'SPEC CPU2006 FP size reduction, part I', 'Spec2006FpSizeReductionPart1')
print()
transform_to_latex(split_table(fp_size)[1], size_percent_filter, column_name_filter, 'SPEC CPU2006 FP size reduction, part II', 'Spec2006IntSizeReductionPart2')
