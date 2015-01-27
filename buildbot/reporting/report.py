#!/usr/bin/env python3

import sys
import os
import json
import argparse

from itertools import *
from html import *

parser = argparse.ArgumentParser(description='Generate HTML reports for SPEC results')
parser.add_argument('folder', metavar = 'FOLDER', help = 'Folder with JSON results')
parser.add_argument('--ignore', dest = 'ignore', help = 'Ignored benchmarks')

args = parser.parse_args()

if args.ignore == None:
  args.ignore = []
else:
  args.ignore = args.ignore.split(',')

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

def generate_comparison(html_root, reports, svg_id): 
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

  row.svg(id = svg_id, style = 'height: 500px; width: 1150px;')
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

def generate_graph(reports, id):
  first_benchmarks = reports[0].benchmarks
  names = list(map(lambda x: x.name, first_benchmarks))

  data = []

  for report in reports:
    values = []
    for i, v in enumerate(first_benchmarks):
      if v.name in report.comparison:
        values.append({'x': i, 'y': report.comparison[v.name]})

    data.append({ 'key': report.full_name, 'values': values })

  return 'var data%u = %s; var legend%u = %s;' % (id, json.dumps(data, indent = 2), id, json.dumps(names, indent = 2))


# HTML REPORT
h = HTML()
head = h.head()
head.meta(charset = 'utf-8')
head.link('', rel = 'stylesheet', href = 'https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.15-beta/nv.d3.css')
head.link('', rel = 'stylesheet', href = 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css')
head.script('', type = 'text/javascript', src = 'https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.3/d3.js')
head.script('', type = 'text/javascript', src = 'https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.15-beta/nv.d3.js') 
head.script('', type = 'text/javascript', src = 'https://code.jquery.com/jquery-2.1.3.js')
head.script('', type = 'text/javascript', src = 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/js/bootstrap.min.js')

keyfunc = lambda x: x.node
benchreports = sorted(benchreports, key = keyfunc, reverse = True)
container = h.body.div(klass = 'container')

counter = 0
script_content = ''

tabpanel = container.div(klass = 'tabpanel')
nav = tabpanel.ul(klass = 'nav nav-tabs', role = 'tablist')
tab_content = container.div(klass = 'tab-content')

first = 'active'
for k, v in groupby(benchreports, keyfunc):
  l = sorted(list(v), key = lambda x: x.full_name)
  for i in l:
    i.compare(l[0])

  id = str(counter)
  tabid = 'tab' + id
  li = nav.li(role = 'presentation', klass = first)
  li.a(k, href = '#' + tabid, role = 'tab', data_toggle = 'tab')

  tab = tab_content.div(role = 'tabpanel', klass = 'tab-pane ' + first, id = tabid)
  first = ''

  tab.h2(k)
  generate_comparison(tab, l, 'data' + id)
  script_content += generate_graph(l, counter)
  first = ''

  script_content += '''var chart;
nv.addGraph(function() {
    chart = nv.models.multiBarChart()
      .margin({bottom: 100})
      .transitionDuration(300)
      .delay(0)
      .rotateLabels(45)
      .groupSpacing(0.1)
      ;

    chart.multibar
      .hideable(true);

    chart.reduceXTicks(false).staggerLabels(true);

    chart.xAxis
        .tickFormat(function(v) { return legend''' + id + '''[v]; });

    chart.yAxis
        .tickFormat(d3.format(',.1f'));

    d3.select("svg#data''' + id + '''")
        .datum(data''' + id + ''')
       .call(chart);

    nv.utils.windowResize(chart.update);

    chart.dispatch.on("stateChange", function(e) { nv.log("New State:", JSON.stringify(e)); });

    return chart;
});
'''

  counter += 1

container.script(script_content)

print(h)
