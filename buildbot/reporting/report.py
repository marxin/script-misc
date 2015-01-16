#!/usr/bin/env python3

import sys
import os
import json
from html import *

if len(sys.argv) < 2:
  exit(1)

data_folder = sys.argv[1]

def average(values):
  return sum(values) / len(values)

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
      self.time = average(d['times'])
      self.size = d['size']['TOTAL']
    else:
      self.time = 0

class BenchMarkReport:
  def __init__ (self, filename, d):
    self.d = d
    self.filename = filename
    all_benchmarks = list(map(lambda x: BenchMarkResult(x, d['FP'][x]), d['FP'])) + list(map(lambda x: BenchMarkResult(x, d['INT'][x]), d['INT']))
    self.benchmarks = sorted(filter(lambda x: x.time != 0, all_benchmarks), key = lambda x: x.name)

  def compare(self, comparer):
    self.comparison = []
    self.size_comparison = []
    
    for i, v in enumerate(self.benchmarks):
      self.comparison.append(round(100.0 * v.time / comparer.benchmarks[i].time, 2))
      self.size_comparison.append(round(100.0 * v.size / comparer.benchmarks[i].size, 2))
    
    self.avg_comparison = round(average(self.comparison), 2)
    self.avg_size_comparison = round(average(self.size_comparison), 2)

benchreports = []

for root, dirs, files in os.walk(data_folder):
  for f in files:
    abspath = os.path.join(root, f)
    benchreports.append(BenchMarkReport(f, json.loads(open(abspath).read())))

benchreports = sorted(benchreports, key = lambda x: x.filename)

for i, v in enumerate(benchreports):
  v.compare(benchreports[0])

# HTML REPORT
h = HTML()

h.head.link(rel = 'stylesheet', href = 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css')

container = h.body.div(klass = 'container')
row = container.div(klass = 'row')

row.h2('Time (smaller is better)')

table = row.table(klass = 'table table-condensed table-bordered')
tr = table.thead.tr
tr.th('')

for b in benchreports:
  tr.th(b.filename)  
  tr.th('time %')

body = table.body

first_benchmarks = benchreports[0].benchmarks

for i in range(len(first_benchmarks)):
  tr = body.tr()
  tr.td(first_benchmarks[i].name)

  for br in benchreports:
    b = br.benchmarks[i]
    tr.td(str(b.time))
    tr.td(str(br.comparison[i]) + ' %', klass = td_class(br.comparison[i]))

tr = body.tr()
tr.td.strong('AVERAGE')

for br in benchreports:
  tr.td()
  td = tr.td(klass = td_class(br.avg_comparison))
  td.strong(str(br.avg_comparison) + ' %')

row.h2('Size (smaller is better)')

table = row.table(klass = 'table table-condensed table-bordered')
tr = table.thead.tr
tr.th('')

for b in benchreports:
  tr.th(b.filename)  
  tr.th('size %')

body = table.body

first_benchmarks = benchreports[0].benchmarks

for i in range(len(first_benchmarks)):
  tr = body.tr()
  tr.td(first_benchmarks[i].name)

  for br in benchreports:
    b = br.benchmarks[i]
    tr.td(str(b.size))
    tr.td(str(br.size_comparison[i]) + ' %', klass = td_class(br.size_comparison[i]))

tr = body.tr()
tr.td.strong('AVERAGE')

for br in benchreports:
  tr.td()
  td = tr.td(klass = td_class(br.avg_size_comparison))
  td.strong(str(br.avg_size_comparison) + ' %')

print(h)
