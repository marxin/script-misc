#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import datetime
import shutil
import json
import commands

benchmarks = [
              ['400.perlbench', True],
              ['401.bzip2', True],
              ['403.gcc', True],
              ['410.bwaves', False],
              ['416.gamess', False],
              ['429.mcf', True],
              ['433.milc', False],
              ['434.zeusmp', False],
              ['435.gromacs', False],
              ['436.cactusADM', False],
              ['437.leslie3d', False],
              ['444.namd', False],
              ['445.gobmk', True],
              ['447.dealII', False],
              ['450.soplex', False],
              ['453.povray', False],
              ['454.calculix', False],
              ['456.hmmer', True],
              ['458.sjeng', True],
              ['459.GemsFDTD', False],
              ['462.libquantum', True],
              ['464.h264ref', True],
              ['465.tonto', False],
              ['470.lbm', False],
              ['471.omnetpp', True],
              ['473.astar', True],
              ['481.wrf', False],
              ['482.sphinx3', False],
              ['483.xalancbmk', True]
            ]

if len(sys.argv) != 3:
  sys.exit(1)

root_path = sys.argv[1]
profile = sys.argv[2]

config_folder = os.path.join(root_path, 'config')
summary_folder = os.path.join(root_path, 'summary')
config_template = os.path.join(config_folder, 'config-template.cfg')

default_flags = '-fno-strict-aliasing -fpeel-loops -ffast-math -march=native -O3'
runspec_arguments = '--size=test --no-reportable --iterations=1 '

os.chdir(root_path)
print(os.getcwd())

def generate_config(profile, extra_flags = ''):
  lines = open(config_template, 'r').readlines()

  p = 94

  flags = default_flags

  lines.insert(p, 'FOPTIMIZE = ' + flags)
  lines.insert(p, 'CXXOPTIMIZE= ' + flags)
  lines.insert(p, 'COPTIMIZE= ' + flags)

  p = 54

  lines.insert(p, 'FC = gfortran')
  lines.insert(p, 'CXX = g++')
  lines.insert(p, 'CC = gcc')

  p = 36

  lines.insert(p, 'ext = ' + profile)

  config_name = os.path.join(config_folder, profile)
  f = open(config_name, 'w+')

  for l in lines:
    f.write(l.strip() + '\n')

  return config_name

def save_spec_log(folder, profile, benchmark, data):
  f = open(os.path.join(folder, profile + '_' + benchmark + '.log'), 'w+')

  for l in data:
    f.write(l)

def parse_csv(path):
  for line in open(path, 'r'):
    tokens = line.split(',')

    if line.startswith('"Selected Results Table"'):
      break
    
    if line.startswith('4') and len(tokens) >= 10 and len(tokens[2]) > 0:
      return float(tokens[2])

def parse_binary_size(folder, profile, benchmark):
  subfolder = os.path.join(root_path, 'benchspec/CPU2006', benchmark, 'exe')
  if not os.path.exists(subfolder):
    return

  binary_file = None

  size = 0

  for exe in os.listdir(subfolder):
    if exe.endswith(profile):
      binary_file = os.path.join(subfolder, exe)
      size = int(os.path.getsize(binary_file))
      break

  f = open(os.path.join(folder, profile + '-size.csv'), 'a+')
  f.write('%s:%u\n' % (benchmark, size))
  f.close()

  path = os.path.join(folder, profile + '-' + benchmark + '-size.csv')

  """
  script_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'readelf_sections.py')

  if binary_file != None:
    command = 'python ' + script_location + ' ' + binary_file + ' csv > ' + path
    r = commands.getstatusoutput(command)
    if r[0] != 0:
      print(r[1])
      exit(2)
  """

def ts_print(*args):
  print('[%s]: ' % datetime.datetime.now(), end = '')

  for a in args:
    print(a)

def get_benchmark_name(benchmark):
  return benchmark[0].split('.')[1]

def runspec_command(cmd):
  return 'source ' + root_path + '/shrc && runspec ' + cmd

# MAIN
print(os.getcwd())

summary_path = os.path.join(summary_folder, profile)
if not os.path.isdir(summary_path):
  os.mkdir(summary_path)

ts_print('Starting group of tests')

d = {}

for j, benchmark in enumerate(reversed(benchmarks)):
  benchmark_name = get_benchmark_name(benchmark)
  d[benchmark_name] = {}

  ts_print('Running subphase: %u/%u: %s' % (j + 1, len(benchmarks), benchmark[0]))

  # Real benchmark run
  extra = ''

  c = generate_config(profile, extra)

  cl = runspec_command('--config=' + c + ' --output-format=csv ' + runspec_arguments + benchmark_name)
  ts_print(cl)
  result = os.popen(cl).readlines()
  save_spec_log(summary_path, profile, get_benchmark_name(benchmark), result)

  csv = ''
  for r in result:
    r = r.strip()
    print(r, file = sys.stderr)
    if r.startswith('format: CSV'):
      csv = r[r.find('/'):].strip()
      d[benchmark_name]['time'] = parse_csv(csv)

  parse_binary_size(summary_path, profile, benchmark[0])

ts_print('Finishing %u/%u: %s' % (i + 1, len(profiles), profile[0]))
ts_print(d)
