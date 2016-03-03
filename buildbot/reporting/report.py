#!/usr/bin/env python3

import sys
import os
import json
import argparse

from itertools import *
from html import *
from functools import *

parser = argparse.ArgumentParser(description='Generate HTML reports for SPEC results')
parser.add_argument('folder', metavar = 'FOLDER', help = 'Folder with JSON results')
parser.add_argument('--ignore', dest = 'ignore', help = 'Ignored benchmarks')
args = parser.parse_args()

def in_good_range(v):
  if v == None:
    return False
  return 0.1 <= v and v <= 5

if args.ignore == None:
  args.ignore = []
else:
  args.ignore = args.ignore.split(',')

def percent(v):
  return '%.2f %%' % v

def ratio(v):
  if v == None:
    return 'N/A'
  return '%.2f' % v

def flt_str(v):
  return '%2.4f' % v if v != 0 else ''

def average(values):
  return sum(values) / len(values)

def geomean(num_list):
  num_list = list(filter(lambda x: x != None, num_list))
  return reduce(lambda x, y: x * y, num_list) ** (1.0 / len(num_list))

def quad_different(values):
  a = geomean(values)
  s = sum(map(lambda x: (x - a)**2, values))
  l = len(values)
  return s / l

def td_class(comparison):
  if not in_good_range(comparison):
    return 'danger'

  if comparison < 1:
    return 'success'
  elif comparison == 1:
    return 'info'
  else:
    return 'warning'

def first(items, f):
    for item in items:
        if f(item):
            return item

    return None

class BenchMarkResult:
    def __init__ (self, d):
        self.name = d['name']
        self.errors = d['errors']
        self.iterations = d['iterations']
        self.average_time = d['average_time']
        self.comparison = None

        assert self.average_time != None or self.errors != ''

    def number(self):
        return self.name.split('_')[0]

    def compare(self, other):
        if other == None:
            return
        elif self.errors != '' or other.errors != '':
            return

        self.comparison = 1.0
        assert other.comparison == None
        # run time smaller than a second is suspicious
        assert self.average_time > 1
        assert other.average_time > 1
        other.comparison = other.average_time / self.average_time

class BenchmarkGroup:
    def __init__ (self, d):
        self.name = d['group_name']
        self.benchmarks = [BenchMarkResult(x) for x in d['benchmarks']]
        self.comparison = None
        assert self.name != None

    def get(self, name):
        return first(self.benchmarks, lambda x: x.name == name)

    def compare(self, other):
        if other == None:
            return None

        for benchmark in self.benchmarks:
            b = other.get(benchmark.name)
            if b != None:
                benchmark.compare(b)

        self.comparison = 1.0
        assert other.comparison == None
        other.comparison = geomean([x.comparison for x in other.benchmarks])

class BenchmarkSuite:
    def __init__ (self, filename, d):
        self.filename = filename
        self.name = d['suitename']
        self.compiler = d['compiler']
        self.toolset = d['toolset']
        self.flags = d['flags']
        self.time = d['time']
        self.groups = [BenchmarkGroup(x) for x in d['groups']]
        self.comparison = None

    def get(self, name):
        return first(self.groups, lambda x: x.name == name)

    def compare(self, other):
        if other == None:
            return None

        all_benchmarks = []
        for group in self.groups:
            g = other.get(group.name)
            if g != None:
                group.compare(g)
                all_benchmarks += g.benchmarks

        self.comparison = 1.0
        assert other.comparison == None
        other.comparison = geomean([x.comparison for x in all_benchmarks])

    def __lt__(self, other):
        if self.compiler == other.compiler:
            return self.flags < other.flags
        else:
            return self.compiler > other.compiler

def generate_comparison(html_root, suites, benchmark_name_fn):
    row = html_root.div()

    row.h2('Time (smaller is better)')

    table = row.table(klass = 'table table-condensed table-bordered')

    # table header
    tr = table.thead.tr
    tr.th('Configuration')

    suite = suites[0]
    tr.th('geomean')
    for g in suite.groups:
        tr.th(g.name, colspan = str(len(g.benchmarks) + 1))

    tr = table.thead.tr
    tr.th('')
    tr.th('')

    for g in suite.groups:
        tr.th('geomean')
        for b in g.benchmarks:
            tr.th(benchmark_name_fn(b))

    # table body
    for suite in suites:
        tr = table.tbody.tr
        tr.td(suite.compiler + ' ' + suite.flags)
        tr.td(ratio(suite.comparison), klass = td_class(suite.comparison))
        for g in suite.groups:
            tr.td(ratio(g.comparison), klass = td_class(g.comparison))
            for b in g.benchmarks:
                tr.td(ratio(b.comparison), klass = td_class(b.comparison))

    return

# MAIN
suites = []
for f in os.listdir(args.folder):
  if f.endswith('.json'):
    abspath = os.path.join(args.folder, f)
    suites.append(BenchmarkSuite(f, json.loads(open(abspath).read())))

suites = sorted(suites)

for suite in suites[1:]:
    suites[0].compare(suite)

# HTML REPORT
h = HTML()
head = h.head()
head.meta(charset = 'utf-8')
head.link('', rel = 'stylesheet', href = 'https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.15-beta/nv.d3.css', media = 'all')
head.link('', rel = 'stylesheet', href = 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css', media = 'all')

body = h.body(style = 'margin: 30px;')
container = body.div()

generate_comparison(container, suites, lambda x: x.number())
generate_comparison(container, suites, lambda x: x.name)

print(h)
