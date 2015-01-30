#!/usr/bin/env python3

import sys
import os
import json
import argparse
import subprocess
import tempfile
import shutil

from itertools import *
from functools import *

def try_makedirs(folder):
  if not os.path.exists(folder):
    os.makedirs(folder)

script_folder = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'build-id.py'))

parser = argparse.ArgumentParser(description='Generate SVG perf reports for various perf.data files')
parser.add_argument('folder', metavar = 'FOLDER', help = 'Folder with perf data')
parser.add_argument('--perf', dest = 'perf', help = 'perf binary location', default = 'perf')
parser.add_argument('--flamegraph', dest = 'flamegraph', help = 'flamegraph project location', required = True)
parser.add_argument('--spec', dest = 'spec', help = 'SPEC source code location')
parser.add_argument('--dry-run', dest = 'dryrun', help = 'Dry run', action = 'store_true')

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
  original_location = open(os.path.join(folder, 'location.txt')).read()
  binary_file = os.path.abspath(os.path.basename(original_location))
  debug = os.path.expanduser('~/.debug')

  print('calling build-id from: ' + binary_file)
  proc = subprocess.Popen([script_folder, binary_file], stdout = subprocess.PIPE)
  id = proc.stdout.read().decode('utf-8').strip()
  proc.communicate()
  id_prefix = id[0:2]
  id = id[2:]

  binary_target = os.path.join(debug, './' + original_location)
  debug_symlink = os.path.join(debug, '.build-id', id_prefix, id)

  print('Symlink: %s->%s' % (debug_symlink, binary_target))

  # print perf report arguments
  if args.spec != None:
    tokens = original_location.split('/')
    benchmark = tokens[-4]
    parts = len(tokens) - 1

    print(parts)
    prefix = os.path.join(os.path.expanduser(args.spec), 'benchspec', 'CPU2006', benchmark, 'src')
    p = '~/Programming/linux/tools/perf/'
    print('Try perf report:\n%sperf report --objdump-prefix=%s --objdump-prefix-strip=%u -i %s' % (p, prefix, parts, os.path.join(folder, 'perf.data')))

  if not args.dryrun:
    # copy binary to .debug folder
    try_makedirs(os.path.dirname(binary_target))
    shutil.copyfile(binary_file, binary_target)

    # create symlink from .debug build ID database
    try_makedirs(os.path.dirname(debug_symlink))

    if not os.path.exists(debug_symlink):
      try:
        os.symlink(binary_target, debug_symlink)
      except FileExistsError:
        pass

    p1 = subprocess.Popen([args.perf, 'script'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen([os.path.join(args.flamegraph, 'stackcollapse-perf.pl')], stdin = p1.stdout, stdout = data_tmp)
    p1.stdout.close()
    p2.communicate()

    # create flamegraph
    svg_path = os.path.join(folder, 'perf-report.svg')
    print('Generating %u/%u: %s' % (i + 1, len(perf_data_locations), svg_path))
    with open(svg_path, 'w') as svg:
      p3 = subprocess.Popen([os.path.join(args.flamegraph, 'flamegraph.pl'), data_tmp.name], stdout = svg)
