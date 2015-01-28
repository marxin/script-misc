#!/usr/bin/env python3

import sys
import os
import json
import argparse
import subprocess
import tempfile

from itertools import *
from functools import *

parser = argparse.ArgumentParser(description='Generate SVG perf reports for various perf.data files')
parser.add_argument('folder', metavar = 'FOLDER', help = 'Folder with perf data')
parser.add_argument('--perf', dest = 'perf', help = 'perf binary location', default = 'perf')
parser.add_argument('--flamegraph', dest = 'flamegraph', help = 'flamegraph project location', required = True)

args = parser.parse_args()

perf_data_locations = []

for root, dirs, files in os.walk(args.folder):
  for f in files:
    if f == 'perf.data':
      perf_data_locations.append(os.path.join(root, f))

for i, perf_data in enumerate(perf_data_locations):
  folder = os.path.dirname(perf_data)
  os.chdir(folder)
  data_tmp = tempfile.NamedTemporaryFile(delete = False)
  print(data_tmp.name)
  p1 = subprocess.Popen([args.perf, 'script', '--symfs=.'], stdout=subprocess.PIPE)
  p2 = subprocess.Popen([os.path.join(args.flamegraph, 'stackcollapse-perf.pl')], stdin = p1.stdout, stdout = data_tmp)
  p1.stdout.close()
  p2.communicate()

  svg_path = os.path.join(folder, 'perf-report.svg')
  print('Generating %u/%u: %s' % (i, len(perf_data_locations), svg_path))
  with open(svg_path, 'w') as svg:
    p3 = subprocess.Popen([os.path.join(args.flamegraph, 'flamegraph.pl'), data_tmp.name], stdout = svg)
