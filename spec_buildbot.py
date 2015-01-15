#!/usr/bin/python

from __future__ import print_function
from tempfile import *

import sys
import os
import datetime
import shutil
import json
import commands
import subprocess

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

if len(sys.argv) != 4:
  sys.exit(1)

real_script_folder = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.abspath(sys.argv[1])
profile = sys.argv[2]

config_folder = os.path.join(root_path, 'config')
summary_folder = os.path.join(root_path, 'summary')
config_template = os.path.join(config_folder, 'config-template.cfg')

default_flags = '-fno-strict-aliasing -fpeel-loops -ffast-math -march=native -O3'
runspec_arguments = '--size=test --no-reportable --iterations=1 '

os.chdir(root_path)

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
    print(line)
    tokens = line.split(',')

    if line.startswith('"Selected Results Table"'):
      break
    
    if line.startswith('4') and len(tokens) >= 10 and len(tokens[2]) > 0:
      print(tokens[2])
      print(line)
      return float(tokens[2])

def parse_binary_size(folder, profile, benchmark):
  subfolder = os.path.join(root_path, 'benchspec/CPU2006', benchmark, 'exe')
  if not os.path.exists(subfolder):
    return None

  binary_file = None
  script_location = os.path.join(real_script_folder, 'readelf.py')

  for exe in os.listdir(subfolder):
    if exe.endswith(profile):
      binary_file = os.path.join(subfolder, exe)
      size = int(os.path.getsize(binary_file))
      break

  d = {}
  if binary_file != None:
    command = 'python ' + script_location + ' --strip --format=csv ' + binary_file
    r = commands.getstatusoutput(command)
    if r[0] != 0:
      print(r[1])
      exit(2)
    else:
      lines = r[1].split('\n')
      for l in lines:
	tokens = l.split(':')
	if len(tokens) == 2:
	  d[tokens[0]] = int(tokens[1])

  return d

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

d = {'INT': {}, 'FP': {}}

for j, benchmark in enumerate(benchmarks):
  benchmark_name = get_benchmark_name(benchmark)

  locald = d['INT']
  if benchmark[1] == False:
    locald = d['FP']

  locald[benchmark_name] = {}

  ts_print('Running subphase: %u/%u: %s' % (j + 1, len(benchmarks), benchmark[0]))

  # Real benchmark run
  extra = ''

  c = generate_config(profile, extra)

  tc_print('Running command: ' + cl)
  cl = runspec_command('--config=' + c + ' --output-format=csv ' + runspec_arguments + benchmark_name)
  proc = commands.getstatusoutput(cl)

  if proc[0] != 0:
    locald[benchmark_name]['time'] = None
    locald[benchmark_name]['size'] = None
    print(proc[1])

  result = proc[1] 
  save_spec_log(summary_path, profile, get_benchmark_name(benchmark), result)

  csv = ''
  for r in result:
    r = r.strip()
    if r.startswith('format: CSV'):
      csv = r[r.find('/'):].strip()
      locald[benchmark_name]['time'] = parse_csv(csv)

  locald[benchmark_name]['size'] = parse_binary_size(summary_path, profile, benchmark[0])

json.dump(d, sys.argv[3], indent = 1)

ts_print(f.name)
