#!/usr/bin/env python

from __future__ import print_function

import os
import sys


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
                  'gcc49-O3-LIPO'
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

  for i in header:
    print('|r', end = '')

  print('|}')
  print('\t\hline')

  #header
  for column in header[:-1]:
    print('\\textbf{' + column_name_filter(column) + '} & ', end = '')

  print('\\textbf{' + column_header_filter(header[-1]) + '} \\\\ \\hline')

  iterate = table[1:-1]

  # body
  for line in iterate:
    for item in line[:-1]:
      print(filt(item) + ' & ', end = '')

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
        d[p][b].append(data[i][base_profile][b][0] / d[p][b][0])
      else:
        d[p][b].append(d[p][b][0] / data[i][base_profile][b][0])

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
        if x > 1.1:
          return color_wrap(s, 'SpecBetter')
        elif x > 1.05:
          return color_wrap(s, 'SpecGood')
        elif x < 0.9:
          return color_wrap(s, 'SpecWorse')
        elif x < 0.95:
          return color_wrap(s, 'SpecBad')
        else:
          return s
      else:
        if x > 1.50:
          return color_wrap(s, 'SpecWorse')
        elif x > 1.25:
          return color_wrap(s, 'SpecBad')
        elif x < 0.50:
          return color_wrap(s, 'SpecBetter')
        elif x < 0.75:
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

  return name

time_summary = [aggregate(data[0], True), aggregate(data[0], True, is_int), aggregate(data[0], True, is_fp)]
size_summary = [aggregate(data[1], True), aggregate(data[1], True, is_int), aggregate(data[1], True, is_fp)]

# 1) performance
all_performance_data = transform_summary(time_summary, ['Performance ', 'Performance (INT)', 'Performance (FP)'])
all_performance = transform_to_table(all_performance_data, row_sorter = sort_profiles)

# 2) size
all_size_data = transform_summary(size_summary, ['Binary size ', 'Binary size (INT)', 'Binary size (FP)'])
all_size = transform_to_table(all_size_data)

# 3) performance for INT profiles and benchmarks
int_performance = transform_to_table(aggregate(data[0], False, is_int), sort_profiles)

# 4) performance for FP profiles and benchmarks
fp_performance = transform_to_table(aggregate(data[0], False, is_fp), sort_profiles)

# 5) size for INT profiles and benchmarks
int_size = transform_to_table(aggregate(data[1], False, is_int), sort_profiles)

# 6) size for FP profiles and benchmarks
fp_size = transform_to_table(aggregate(data[1], False, is_fp), sort_profiles)

print('\n% 1) performance')

transform_to_latex(all_performance, simple_percent_filter, column_name_filter, 'SPEC2006 performance', 'Spec2006Performance', False)
print()

print('\n% 2) size')
transform_to_latex(all_size, simple_percent_filter, column_name_filter, 'SPEC2006 binary size', 'Spec2006BinarySize', False)

print()

print('\n% 3) int_performance')

transform_to_latex(split_table(int_performance)[0], time_percent_filter, column_name_filter, 'SPEC2006 INT performance, part I', 'Spec2006IntPerformancePart1')
print()
transform_to_latex(split_table(int_performance)[1], time_percent_filter, column_name_filter, 'SPEC2006 INT performance, part II', 'Spec2006IntPerformancePart2')
print()

print('\n% 4) fp_performance')
transform_to_latex(split_table(fp_performance)[0], time_percent_filter, column_name_filter, 'SPEC2006 FP performance, part I', 'Spec2006FpPerformancePart1')
print()
transform_to_latex(split_table(fp_performance)[1], time_percent_filter, column_name_filter, 'SPEC2006 FP performance, part II', 'Spec2006FpPerformancePart2')
print()

print('\n% 5) int_size')
transform_to_latex(split_table(int_size)[0], size_percent_filter, column_name_filter, 'SPEC2006 INT binary size, part I', 'Spec2006IntSizePart1')
print()
transform_to_latex(split_table(int_size)[1], size_percent_filter, column_name_filter, 'SPEC2006 INT binary size, part II', 'Spec2006IntSizePart2')

print('\n% 6) fp_size')
transform_to_latex(split_table(fp_size)[0], size_percent_filter, column_name_filter, 'SPEC2006 FP binary size, part I', 'Spec2006FpSizePart1')
print()
transform_to_latex(split_table(fp_size)[1], size_percent_filter, column_name_filter, 'SPEC2006 FP binary size, part II', 'Spec2006IntSizePart2')
