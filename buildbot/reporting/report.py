#!/usr/bin/env python3

import sys
import os
import json
import argparse

from itertools import *
from html import *

parser = argparse.ArgumentParser(description='Generate HTML reports for SPEC results')
parser.add_argument('folder', metavar = 'FOLDER', help = 'Folder with JSON results')
parser.add_argument('--ignore', dest = 'ignore', nargs = '+', help = 'Ignored benchmarks')

args = parser.parse_args()

if args.ignore == None:
  args.ignore = []

def percent(v):
  return '%.2f %%' % v

def flt_str(v):
  return '%2.4f' % v

def average(values):
  return sum(values) / len(values)

def quad_different(values):
  a = average(values)
  s = sum(map(lambda x: (x - a)**2, values))
  l = len(values)
  return s / l

def td_class(comparison):
  if comparison < 100:
    return 'success'
  elif comparison == 100:
    return 'info'
  else:
    return 'danger'

class BenchMarkResult:
  def __init__ (self, name, d):
    self.name = name
    self.d = d

    if len(d['times']) > 0:
      self.all_times = d['times']
      self.time = average(d['times'])
      self.time_quad_difference = round(quad_different(d['times']), 4)
      self.size = d['size']['TOTAL']
    else:
      self.time = 0

class BenchMarkReport:
  def __init__ (self, filename, d):
    self.d = d
    self.filename = filename
    self.node = self.d['info']['node']
    self.changes = self.d['info']['changes'].replace('buildbot: poke', '')
    self.compiler = self.d['info']['compiler']
    self.full_name = self.compiler + '#' + self.changes
    all_benchmarks = list(map(lambda x: BenchMarkResult(x, d['FP'][x]), d['FP'])) + list(map(lambda x: BenchMarkResult(x, d['INT'][x]), d['INT']))
    self.benchmarks = sorted(filter(lambda x: x.time != 0 and not x.name in args.ignore, all_benchmarks), key = lambda x: x.name)
    self.benchmarks_dictionary = {}
    for b in self.benchmarks:
      self.benchmarks_dictionary[b.name] = b

  def compare(self, comparer):
    self.comparison = {}
    self.size_comparison = {}
    
    for i, v in enumerate(self.benchmarks):
      if v.name in comparer.benchmarks_dictionary:
        self.comparison[v.name] = round(100.0 * v.time / comparer.benchmarks_dictionary[v.name].time, 2)
        self.size_comparison[v.name] = round(100.0 * v.size / comparer.benchmarks_dictionary[v.name].size, 2)
    
    self.avg_comparison = round(average(self.comparison.values()), 2)
    self.avg_size_comparison = round(average(self.size_comparison.values()), 2)

benchreports = []

for root, dirs, files in os.walk(args.folder):
  for f in files:
    abspath = os.path.join(root, f)
    benchreports.append(BenchMarkReport(f, json.loads(open(abspath).read())))

def generate_comparison(html_root, reports): 
  row = html_root.div(klass = 'row')

  row.h2('Time (smaller is better)')

  table = row.table(klass = 'table table-condensed table-bordered')
  tr = table.thead.tr
  tr.th('')

  for b in reports:
    tr.th(b.full_name)
    tr.th('time %')

  body = table.body

  first_benchmarks = reports[0].benchmarks

  for i in first_benchmarks:
    tr = body.tr()
    tr.td(i.name)

    for br in reports:
      if i.name in br.benchmarks_dictionary:
        b = br.benchmarks_dictionary[i.name]
#      tr.td(str(b.time) + '(QD:' + str(b.time_quad_difference) + ')')
        tr.td(flt_str(b.time), klass = "text-right")
        tr.td(percent(br.comparison[i.name]), klass = td_class(br.comparison[i.name]) + ' text-right')
      else:
        tr.td('N/A', klass = 'text-right')
        tr.td('N/A', klass = 'text-right')

  tr = body.tr()
  tr.td.strong('AVERAGE')

  for br in reports:
    tr.td()
    td = tr.td(klass = td_class(br.avg_comparison) + ' text-right')
    td.strong(percent(br.avg_comparison))

  row.h2('Size (smaller is better)')

  table = row.table(klass = 'table table-condensed table-bordered')
  tr = table.thead.tr
  tr.th('')

  for b in reports:
    tr.th(b.full_name)
    tr.th('size %')

  body = table.body

  first_benchmarks = reports[0].benchmarks

  for i in first_benchmarks:
    tr = body.tr()
    tr.td(i.name)

    for br in reports:
      if i.name in br.benchmarks_dictionary:
        b = br.benchmarks_dictionary[i.name]
        tr.td(str(b.size), klass = 'text-right')
        tr.td(percent(br.size_comparison[i.name]), klass = td_class(br.size_comparison[i.name]) + ' text-right')
      else:
        tr.td('N/A', klass = 'text-right')
        tr.td('N/A', klass = 'text-right')

  tr = body.tr()
  tr.td.strong('AVERAGE')

  for br in reports:
    tr.td()
    td = tr.td(klass = td_class(br.avg_size_comparison) + ' text-right')
    td.strong(percent(br.avg_size_comparison))

# HTML REPORT
h = HTML()
h.head.link(rel = 'stylesheet', href = 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css')

keyfunc = lambda x: x.node
benchreports = sorted(benchreports, key = keyfunc)
container = h.body.div(klass = 'container')

for k, v in groupby(benchreports, keyfunc):
  l = sorted(list(v), key = lambda x: x.full_name)
  for i in l:
    i.compare(l[0])

  container.h2(k)
  generate_comparison(container, l)

print(h)
