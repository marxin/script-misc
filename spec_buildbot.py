#!/usr/bin/python

from __future__ import print_function
from tempfile import *
from base64 import *
from distutils.version import LooseVersion
from subprocess import *
from multiprocessing import *

import sys
import os
import glob
import datetime
import shutil
import json
import commands
import platform
import subprocess
import tarfile

### SPECv6 class ###
class CpuV6:
  def get_benchmarks(self):
    return [
    Benchmark('600.perlbench_s', True),
    Benchmark('602.gcc_s', True),
    Benchmark('603.bwaves_s', False),
    Benchmark('605.mcf_s', True),
    Benchmark('607.cactuBSSN_s', False),
    Benchmark('608.namd_s', False),
    Benchmark('610.parest_s', False),
    Benchmark('611.povray_s', False),
    Benchmark('613.hmmer_s', True),
    Benchmark('619.lbm_s', False),
    Benchmark('620.omnetpp_s', True),
    Benchmark('621.wrf_s', False),
    Benchmark('623.xalancbmk_s', True),
    Benchmark('625.x264_s', True),
    Benchmark('626.blender_s', False),
    Benchmark('627.cam4_s', False),
    Benchmark('628.pop2_s', True),
    Benchmark('631.deepsjeng_s', True),
    Benchmark('632.facesim_s', False),
    Benchmark('638.imagick_s', False),
    Benchmark('639.bodytrack_s', False),
    Benchmark('641.leela_s', True),
    Benchmark('644.nab_s', False),
    Benchmark('647.drops_s', False),
    Benchmark('648.exchange2_s', True),
    Benchmark('649.fotonik3d_s', False),
    Benchmark('651.qe_s', False),
    Benchmark('652.mdwp_s', True), 
    Benchmark('653.johnripper_s', True),
    Benchmark('654.roms_s', False),
    Benchmark('656.ferret_s', False),
    Benchmark('657.xz_s', True)]

  def build_config(self, configuration, profile):
    config_template_path = os.path.join(real_script_folder, 'config-template', 'config-template-v6.cfg')
    lines = open(config_template_path, 'r').readlines()

    p = 133

    flags = default_flags
    lines.insert(p, 'OPTIMIZE = ' + flags)

    p = 114
    lines.insert(p, 'makeflags = -j' + str(cpu_count()))

    p = 54

    compilers = configuration.compilers()
    lines.insert(p, 'FC = ' + compilers['FC'])
    lines.insert(p, 'CXX = ' + compilers['CXX'])
    lines.insert(p, 'CC = ' + compilers['CC'])
    lines.insert(p, 'EXTRA_LDFLAGS = ' + compilers['LD'])

    config_name = os.path.join(config_folder, profile + '.cfg')
    f = open(config_name, 'w+')

    for l in lines:
      f.write(l.strip() + '\n')

    ts_print('generating config to: ' + config_name)
    return config_name


### SPEC2006 class ###
class Cpu2006:
  def get_benchmarks(self):
    return [
      Benchmark('400.perlbench', True, False),
      Benchmark('401.bzip2', True, False),
      Benchmark('403.gcc', True, False),
      Benchmark('410.bwaves', False, True),
      Benchmark('416.gamess', False, True),
      Benchmark('429.mcf', True, False),
      Benchmark('433.milc', False, False),
      Benchmark('434.zeusmp', False, True),
      Benchmark('435.gromacs', False, True),
      Benchmark('436.cactusADM', False, True),
      Benchmark('437.leslie3d', False, True),
      Benchmark('444.namd', False, False),
      Benchmark('445.gobmk', True, False),
      Benchmark('447.dealII', False, False),
      Benchmark('450.soplex', False, False),
      Benchmark('453.povray', False, False),
      Benchmark('454.calculix', False, True),
      Benchmark('456.hmmer', True, False),
      Benchmark('458.sjeng', True, False),
      Benchmark('459.GemsFDTD', False, True),
      Benchmark('462.libquantum', True, False),
      Benchmark('464.h264ref', True, False),
      Benchmark('465.tonto', False, True),
      Benchmark('470.lbm', False, False),
      Benchmark('471.omnetpp', True, False),
      Benchmark('473.astar', True, False),
      Benchmark('481.wrf', False, True),
      Benchmark('482.sphinx3', False, False),
      Benchmark('483.xalancbmk', True, False)
    ]

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
    lines.insert(p, 'EXTRA_LDFLAGS = ' + compilers['LD'])

    p = 36

    lines.insert(p, 'ext = ' + profile)

    config_name = os.path.join(config_folder, profile)
    f = open(config_name, 'w+')

    for l in lines:
      f.write(l.strip() + '\n')

    ts_print('generating config to: ' + config_name)
    return config_name

### compiler configurations ###
class GCCConfiguration:
  def filter_benchmarks(self, benchmarks):
    return benchmarks
  def compilers(self):
    return { 'FC': 'gfortran', 'CXX': 'g++', 'CC': 'gcc', 'LD': '' }

class LLVMConfiguration:
  def filter_benchmarks(self):
    return benchmarks
  def compilers(self):
    return { 'FC': '___no_cf___', 'CXX': 'clang++', 'CC': 'clang', 'LD': '' }

class ICCConfiguration:
  def filter_benchmarks(self, benchmarks):
    return benchmarks
  def compilers(self):
    prefix = '~matz/bin/2015.1/bin/intel64/'
    return { 'FC': os.path.join(prefix, 'ifort'), 'CXX': os.path.join(prefix, 'icpc'), 'CC': os.path.join(prefix, 'icc'), 'LD': '/suse/mliska/override-intel.o /suse/matz/bin/2015.1/compiler/lib/intel64/libirc.a' }

class Benchmark:
  def __init__(self, name, is_int):
    self.name = name
    self.pure_name = name[name.find('.') + 1:]
    self.is_int = is_int

if len(sys.argv) != 6:
  sys.exit(1)

real_script_folder = os.path.dirname(os.path.realpath(__file__))

# ARGUMENT parsing
root_path = os.path.abspath(sys.argv[1])
dump_file = sys.argv[2]
compiler = sys.argv[3]
changes = b64decode(sys.argv[4])
perf_folder = sys.argv[5]
profile = 'cpuv6'

configuration = None
if compiler == 'gcc':
  configuration = GCCConfiguration()
elif compiler == 'llvm':
  configuration = LLVMConfiguration()
elif compiler == 'icc':
  configuration = ICCConfiguration()

config_folder = os.path.join(root_path, 'config')
summary_folder = os.path.join(root_path, 'summary')
config_template = os.path.join(real_script_folder, 'config-template', 'config-template.cfg')

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

perf_arguments = ['--call-graph=dwarf']
if LooseVersion(perf_version) < LooseVersion('3.0.0'):
  perf_arguments = ['-g', '-f']

# TODO
perf_arguments = []

def save_spec_log(folder, profile, benchmark, data):
  f = open(os.path.join(folder, profile + '_' + benchmark + '.log'), 'w+')

  for l in data:
    f.write(l)

def parse_rsf(path):
  lines = open(path, 'r').readlines()
  reported = [l for l in lines if 'reported_time' in l]
  results = []
  has_error = any(map(lambda x: 'non-zero return code' in x, lines))

  for report in reported:
    time = report.split(':')[-1].strip()
    if time != '--':
      results.append(float(time))

  return (results, has_error)

def parse_binary_size(binary_file):
  d = {}
  script_location = os.path.join(real_script_folder, 'readelf.py')
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

def runspec_command(cmd):
  return 'source ' + root_path + '/shrc && runspec ' + cmd

def get_binary_for_spec(spec):
  p = os.path.join(root_path, 'benchspec', 'CPUv6', spec, 'exe')
  newest = max(glob.iglob(p +'/*'), key=os.path.getctime)
  binary = os.path.join(p, newest)
  ts_print(binary)

# MAIN
summary_path = os.path.join(summary_folder, profile)
if not os.path.isdir(summary_path):
  os.makedirs(summary_path)

ts_print('Starting group of tests')


v6 = CpuV6()
benchmarks = configuration.filter_benchmarks(v6.get_benchmarks()[7:10])
c = v6.build_config(configuration, profile)

for j, b in enumerate(benchmarks):
  locald = d['INT'] if b.is_int else d['FP']
  locald[b.name] = {}

  ts_print('Running subphase: %u/%u: %s' % (j + 1, len(benchmarks), b.name))

  # Real benchmark run
  extra = ''

  cl = runspec_command('--config=' + c + ' --output-format=raw ' + runspec_arguments + b.name)
  proc = commands.getstatusoutput(cl)

  ts_print('Command result: %u' % proc[0])
  if proc[0] != 0:
    locald[b.name]['times'] = None
    locald[b.name]['size'] = None
    print('runspec command has failed')
    print(proc[1])
  else:
    result = proc[1] 
    save_spec_log(summary_path, profile, b.name, result)

    rsf = ''
    for r in result.split('\n'):
      r = r.strip()
      if r.startswith('format: raw'):
	rsf = r[r.find('/'):].strip()
	ts_print(rsf)
	rsf_result = parse_rsf(rsf)
	locald[b.name]['times'] = rsf_result[0]
	locald[b.name]['error'] = rsf_result[1]

    # prepare folder
    perf_folder_subdir = os.path.join(perf_folder, b.name)
    os.makedirs(perf_folder_subdir)

    # process PERF record
    if rsf != None:
      log_path = os.path.dirname(rsf)
      t = os.path.basename(rsf).split('.')
      log_path = os.path.join(log_path, '.'.join(t[0:2] + ['log']))
      log_path = os.path.join(log_path, log_path)

      # reading log file
      invoke = [x for x in open(log_path).readlines() if x.startswith('Specinvoke')][0].strip()
      invoke = invoke[invoke.find(' ') + 1:]

      perf_abspath = os.path.join(perf_folder_subdir, 'perf.data')
      if os.path.isfile('perf.data'):
        os.remove('perf.data')

      perf_cmd = ['perf', 'record'] + perf_arguments + ['--'] + invoke.split(' ')
      ts_print('Running perf command: "' + str(perf_cmd) + '"')
      FNULL = open(os.devnull, 'w')
      proc = Popen(perf_cmd, stdout = FNULL, stderr = PIPE)
      stdout, stderr = proc.communicate()
      if proc.returncode != 0:
	ts_print('Perf command failed: ' + stderr.decode('utf-8'))
      else:
	shutil.copyfile('perf.data', perf_abspath)

	binary_folder = invoke.split(' ')[2]
	binary = os.path.join(binary_folder, [x for x in os.listdir(binary_folder) if x.endswith('compsys')][0])
        binary_target = os.path.join(perf_folder_subdir, os.path.basename(binary))
	ts_print('Copy binary file: %s -> %s' % (binary, binary_target))
	shutil.copyfile(binary, binary_target)
	log_target = os.path.join(perf_folder_subdir, 'spec.log')
	ts_print('Copy SPEC log file: %s -> %s' % (log_path, log_target))
	shutil.copyfile(log_path, log_target)
        ts_print('Writing original path to: ' + binary)
        with open(os.path.join(perf_folder_subdir, 'location.txt'), 'w') as f:
          f.write(binary)	

        locald[b.name]['size'] = parse_binary_size(binary)

  ts_print(locald)

with open(dump_file, 'w') as fp:
  json.dump(d, fp, indent = 1)

ts_print(json.dumps(d, indent = 1))
