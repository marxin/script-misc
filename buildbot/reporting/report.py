#!/usr/bin/env python3

import sys
import os
import json
from itertools import *
from html import *

if len(sys.argv) < 2:
  exit(1)

data_folder = sys.argv[1]

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
    self.changes = self.d['info']['changes']
    self.compiler = self.d['info']['compiler']
    all_benchmarks = list(map(lambda x: BenchMarkResult(x, d['FP'][x]), d['FP'])) + list(map(lambda x: BenchMarkResult(x, d['INT'][x]), d['INT']))
    self.benchmarks = sorted(filter(lambda x: x.time != 0, all_benchmarks), key = lambda x: x.name)
    self.benchmarks_dictionary = {}
    for b in self.benchmarks:
      self.benchmarks_dictionary[b.name] = b

  def compare(self, comparer):
    self.comparison = []
    self.size_comparison = []
    
    for i, v in enumerate(self.benchmarks):
      if v.name in comparer.benchmarks_dictionary:
        self.comparison.append(round(100.0 * v.time / comparer.benchmarks_dictionary[v.name].time, 2))
        self.size_comparison.append(round(100.0 * v.size / comparer.benchmarks_dictionary[v.name].size, 2))
    
    self.avg_comparison = round(average(self.comparison), 2)
    self.avg_size_comparison = round(average(self.size_comparison), 2)

benchreports = []

for root, dirs, files in os.walk(data_folder):
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
    tr.th(b.compiler + '#' + b.changes)
    tr.th('time %')

  body = table.body

  first_benchmarks = reports[0].benchmarks

  for i in range(len(first_benchmarks)):
    tr = body.tr()
    tr.td(first_benchmarks[i].name)

    for br in reports:
      b = br.benchmarks[i]
      tr.td(str(b.time) + '(QD:' + str(b.time_quad_difference) + ')')
      tr.td(str(br.comparison[i]) + ' %', klass = td_class(br.comparison[i]))

  tr = body.tr()
  tr.td.strong('AVERAGE')

  for br in reports:
    tr.td()
    td = tr.td(klass = td_class(br.avg_comparison))
    td.strong(str(br.avg_comparison) + ' %')

  row.h2('Size (smaller is better)')

  table = row.table(klass = 'table table-condensed table-bordered')
  tr = table.thead.tr
  tr.th('')

  for b in reports:
    tr.th(b.compiler + '#' + b.changes)
    tr.th('size %')

  body = table.body

  first_benchmarks = reports[0].benchmarks

  for i in range(len(first_benchmarks)):
    tr = body.tr()
    tr.td(first_benchmarks[i].name)

    for br in reports:
      b = br.benchmarks[i]
      tr.td(str(b.size))
      tr.td(str(br.size_comparison[i]) + ' %', klass = td_class(br.size_comparison[i]))

  tr = body.tr()
  tr.td.strong('AVERAGE')

  for br in reports:
    tr.td()
    td = tr.td(klass = td_class(br.avg_size_comparison))
    td.strong(str(br.avg_size_comparison) + ' %')

# HTML REPORT
h = HTML()
h.head.link(rel = 'stylesheet', href = 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css')

keyfunc = lambda x: x.node
benchreports = sorted(benchreports, key = keyfunc)
container = h.body.div(klass = 'container')

for k, v in groupby(benchreports, keyfunc):
  l = list(v)
  for i in l:
    i.compare(l[0])

  container.h2(k)
  generate_comparison(container, l)

print(h)
