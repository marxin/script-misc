#!/usr/bin/python

from __future__ import print_function
from tempfile import *
from base64 import *
from distutils.version import LooseVersion

import sys
import os
import datetime
import shutil
import json
import commands
import subprocess
import platform

# columns: [benchmark name, INT component, is fortran]
benchmarks = [
              ['400.perlbench', True, False],
              ['401.bzip2', True, False],
              ['403.gcc', True, False],
              ['410.bwaves', False, True],
              ['416.gamess', False, True],
              ['429.mcf', True, False],
              ['433.milc', False, False],
              ['434.zeusmp', False, True],
              ['435.gromacs', False, True],
              ['436.cactusADM', False, True],
              ['437.leslie3d', False, True],
              ['444.namd', False, False],
              ['445.gobmk', True, False],
              ['447.dealII', False, False],
              ['450.soplex', False, False],
              ['453.povray', False, False],
              ['454.calculix', False, True],
              ['456.hmmer', True, False],
              ['458.sjeng', True, False],
              ['459.GemsFDTD', False, True],
              ['462.libquantum', True, False],
              ['464.h264ref', True, False],
              ['465.tonto', False, True],
              ['470.lbm', False, False],
              ['471.omnetpp', True, False],
              ['473.astar', True, False],
              ['481.wrf', False, True],
              ['482.sphinx3', False, False],
              ['483.xalancbmk', True, False]
            ]

class GCCConfiguration:
  def get_benchmarks(self):
    # dealII runs extremely slowly
    return list(filter(lambda x: x[0] != '447.dealII', benchmarks))
  def compilers(self):
    return { 'FC': 'gfortran', 'CXX': 'g++', 'CC': 'gcc' }

class LLVMConfiguration:
  def get_benchmarks(self):
    # dealII runs extremely slowly
    return list(filter(lambda x: x[2] == False and x[0] != '447.dealII', benchmarks))
  def compilers(self):
    return { 'FC': '___no_cf___', 'CXX': 'clang++', 'CC': 'clang' }

class ICCConfiguration:
  def get_benchmarks(self):
    # dealII runs extremely slowly
    return benchmarks
  def compilers(self):
    prefix = '~matz/bin/2015.1/bin/intel64/'
    return { 'FC': os.path.join(prefix, 'ifort'), 'CXX': os.path.join(prefix, 'icpc'), 'CC': os.path.join(prefix, 'icc') }

if len(sys.argv) != 7:
  sys.exit(1)

real_script_folder = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.abspath(sys.argv[1])
profile = sys.argv[2]
dump_file = sys.argv[3]
compiler = sys.argv[4]
changes = b64decode(sys.argv[5])
perf_folder = sys.argv[6]

configuration = None
if compiler == 'gcc':
  configuration = GCCConfiguration()
elif compiler == 'llvm':
  configuration = LLVMConfiguration()
elif compiler == 'icc':
  configuration = ICCConfiguration()

config_folder = os.path.join(root_path, 'config')
summary_folder = os.path.join(root_path, 'summary')
config_template = os.path.join(config_folder, 'config-template.cfg')

default_flags = '-Ofast -march=native -g'
runspec_arguments = '--size=test --no-reportable --iterations=5 --tune=peak '

d = {
    'INT': {},
    'FP': {},
    'info':
      {
	'flags': default_flags,
	'runspec_flags': runspec_arguments,
	'uname': ' '.join(platform.uname()),
	'node': platform.uname()[1],
	'changes': changes,
	'compiler': compiler
      }
    }

os.chdir(root_path)

# perf argument detection
proc = commands.getstatusoutput('perf --version')
perf_version = proc[1].split(' ')[-1]

perf_arguments = ' --call-graph=dwarf '
if LooseVersion(perf_version) < LooseVersion('3.0.0'):
  perf_arguments = '-g'

def generate_config(profile, configuration, extra_flags = ''):
  lines = open(config_template, 'r').readlines()

  p = 94

  flags = default_flags

  lines.insert(p, 'FOPTIMIZE = ' + flags)
  lines.insert(p, 'CXXOPTIMIZE= ' + flags)
  lines.insert(p, 'COPTIMIZE= ' + flags)

  p = 54

  compilers = configuration.compilers()
  lines.insert(p, 'FC = ' + compilers['FC'])
  lines.insert(p, 'CXX = ' + compilers['CXX'])
  lines.insert(p, 'CC = ' + compilers['CC'])

  p = 36

  lines.insert(p, 'ext = ' + profile)

  config_name = os.path.join(config_folder, profile)
  f = open(config_name, 'w+')

  for l in lines:
    f.write(l.strip() + '\n')

  ts_print('generating config to: ' + config_name)
  return config_name

def save_spec_log(folder, profile, benchmark, data):
  f = open(os.path.join(folder, profile + '_' + benchmark + '.log'), 'w+')

  for l in data:
    f.write(l)

def parse_rsf(path):
  reported = [l for l in open(path, 'r').readlines() if 'reported_time' in l]
  results = []

  for report in reported:
    time = report.split(':')[-1].strip()
    if time != '--':
      results.append(float(time))

  return results

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

  sys.stdout.flush()

def get_benchmark_name(benchmark):
  return benchmark[0].split('.')[1]

def runspec_command(cmd):
  return 'source ' + root_path + '/shrc && runspec ' + cmd

# MAIN
summary_path = os.path.join(summary_folder, profile)
if not os.path.isdir(summary_path):
  os.mkdir(summary_path)

ts_print('Starting group of tests')

benchmarks = configuration.get_benchmarks()

for j, benchmark in enumerate(benchmarks):
  benchmark_name = get_benchmark_name(benchmark)

  locald = d['INT']
  if benchmark[1] == False:
    locald = d['FP']

  locald[benchmark_name] = {}

  ts_print('Running subphase: %u/%u: %s' % (j + 1, len(benchmarks), benchmark[0]))

  # Real benchmark run
  extra = ''

  c = generate_config(profile, configuration, extra)

  cl = runspec_command('--config=' + c + ' --output-format=raw ' + runspec_arguments + benchmark_name)
  proc = commands.getstatusoutput(cl)

  ts_print('Command result: %u' % proc[0])
  if proc[0] != 0:
    locald[benchmark_name]['times'] = None
    locald[benchmark_name]['size'] = None
    print('runspec command has failed')
    print(proc[1])
  else:
    result = proc[1] 
    save_spec_log(summary_path, profile, get_benchmark_name(benchmark), result)

    rsf = ''
    invoke = None
    for r in result.split('\n'):
      r = r.strip()
      if r.startswith('format: raw'):
	rsf = r[r.find('/'):].strip()
	locald[benchmark_name]['times'] = parse_rsf(rsf)
      if 'specinvoke' in r and invoke == None:
	invoke = r

    # prepare folder
    perf_folder_subdir = os.path.join(perf_folder, benchmark_name)
    os.makedirs(perf_folder_subdir)

    # process PERF record
    if invoke != None:
      ts_print(os.getcwd())
      perf_abspath = os.path.join(perf_folder_subdir, 'perf.data')
      perf_cmd = 'perf record -o ' + perf_abspath + perf_arguments + ' -- ' + invoke
      ts_print('Running perf command: "' + perf_cmd + '"')
      proc = commands.getstatusoutput(perf_cmd)
      if proc[0] != 0:
	ts_print('Perf command failed: ' + proc[1])
      else:
	binary_folder = invoke.split(' ')[2]
	binary = os.path.join(binary_folder, [x for x in os.listdir(binary_folder) if profile in x][0])
	dst = os.path.join(perf_folder_subdir, os.path.basename(binary))
	ts_print('Copy binary: %s to: %s' % (binary, dst))
	shutil.copyfile(binary, dst)
	ts_print('Writing original path to: ' + binary)
	with open(os.path.join(perf_folder_subdir, 'location.txt'), 'w') as f:
	  f.write(binary)

  locald[benchmark_name]['size'] = parse_binary_size(summary_path, profile, benchmark[0])
  ts_print(locald)

with open(dump_file, 'w') as fp:
  json.dump(d, fp, indent = 1)

ts_print(json.dumps(d, indent = 1))
