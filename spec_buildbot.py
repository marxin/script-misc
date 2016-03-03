#!/usr/bin/env python3

from tempfile import *
from base64 import *
from distutils.version import LooseVersion
from subprocess import *
from multiprocessing import *
from subprocess import Popen, PIPE

import sys
import os
import glob
import datetime
import shutil
import json
import platform
import subprocess
import tarfile
import sys
import argparse

runspec_arguments = '--size=test --no-reportable --iterations=1 --tune=peak --no-reportable -I -D '

# ARGUMENT parsing
parser = argparse.ArgumentParser(description='Run SPEC benchmarks and save the result to a log file')
parser.add_argument('root_path', metavar = 'root_path', help = 'Root folder of SPEC benchmarks')
parser.add_argument('log_file', metavar = 'log_file', help = 'Output log file')
parser.add_argument('compiler', metavar = 'compiler', help = 'Compiler: [gcc,llvm,icc]')
parser.add_argument('flags', metavar = 'flags', help = 'Encoded flags in base64')

args = parser.parse_args()

default_flags = '-march=native -g'
flags = default_flags + ' ' + b64decode(args.flags).decode('utf-8')
profile = 'cpuv6'

def runspec_command(cmd):
  return 'source ./shrc && runspec ' + cmd

def run_command(cmd):
    proc = Popen(cmd, stdout=PIPE, bufsize=1, shell = True)
    output = ''
    for line in iter(proc.stdout.readline, ''):
        c = line.decode('utf-8')
        if c == '':
            break
        output += c
        print(c, end = '')
        sys.stdout.flush()
    proc.communicate()

    # save the output to a log file
    with open(args.log_file, 'w') as fp:
        fp.write(output)
    return proc.returncode

### SPECv6 class ###
class CpuV6:
  def build_config(self, configuration, profile, flags):
    config_template_path = os.path.join(real_script_folder, 'config-template', 'config-template-v6.cfg')
    compilers = configuration.compilers()
    lines = [x.strip() for x in open(config_template_path, 'r').readlines()]

    new_lines = []
    for line in lines:
        if line == 'JOBS_PLACEHOLDER':
            new_lines.append('makeflags = -j' + str(cpu_count()))
        elif line == 'OPTIMIZE_PLACEHOLDER':
            new_lines.append('OPTIMIZE = ' + flags)
        elif line == 'COMPILERS_PLACEHOLDER':
            new_lines.append('FC = ' + compilers['FC'])
            new_lines.append('CXX = ' + compilers['CXX'])
            new_lines.append('CC = ' + compilers['CC'])
            new_lines.append('EXTRA_LDFLAGS = ' + compilers['LD'])
        else:
            new_lines.append(line)

    config_filename = profile + '.cfg'
    config_path = os.path.join(config_folder, config_filename)
    f = open(config_path, 'w+')
    f.write('\n'.join(new_lines))

    ts_print('generating config to: ' + config_path)
    return config_filename

  def build_command_line(self, c):
    all_tests = sorted('557.xz_r 500.perlbench_r 525.x264_r 544.nab_r 553.johnripper_r 505.mcf_r 547.drops_r 502.gcc_r 523.xalancbmk_r 508.namd_r 549.fotonik3d_r 503.bwaves_r 510.parest_r 548.exchange2_r 531.deepsjeng_r 513.hmmer_r 526.blender_r 552.mdwp_r 532.facesim_r 511.povray_r 556.ferret_r 519.lbm_r 539.bodytrack_r 520.omnetpp_r 507.cactuBSSN_r 527.cam4_r 521.wrf_r 538.imagick_r 541.leela_r 554.roms_r'.split(' '))

    slow_tests = set(['bwaves', 'wrf', 'roms'])
    tests = list(filter(lambda x: not any(map(lambda y: y in x, slow_tests)), all_tests))
    ts_print('Running tests: %d' % len(tests))

    return runspec_command('--config=' + c + ' --output-format=raw ' + runspec_arguments + ' '.join(tests))

### SPEC2006 class ###
class Cpu2006:
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
  def filter_benchmarks(self, benchmarks):
    return benchmarks
  def compilers(self):
    return { 'FC': '___no_cf___', 'CXX': 'clang++', 'CC': 'clang', 'LD': '' }

class ICCConfiguration:
  def filter_benchmarks(self, benchmarks):
    return benchmarks
  def compilers(self):
    return { 'FC': 'ifort', 'CXX': 'icpc', 'CC': 'icc', 'LD': '' } #, 'LD': '/suse/mliska/override-intel.o /suse/matz/bin/2015.1/compiler/lib/intel64/libirc.a' }

class Benchmark:
  def __init__(self, name, is_int):
    self.name = name
    self.pure_name = name[name.find('.') + 1:]
    self.is_int = is_int

real_script_folder = os.path.dirname(os.path.realpath(__file__))

configuration = None
if args.compiler == 'gcc':
  configuration = GCCConfiguration()
elif args.compiler == 'llvm':
  configuration = LLVMConfiguration()
elif args.compiler == 'icc':
  configuration = ICCConfiguration()

config_folder = 'config'
summary_folder = 'summary'
config_template = os.path.join(real_script_folder, 'config-template', 'config-template.cfg')


def ts_print(*args):
  print('[%s]: ' % datetime.datetime.now(), end = '')

  for a in args:
    print(a)

  sys.stdout.flush()

ts_print('chdir: %s' % args.root_path)
os.chdir(args.root_path)

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
    r = subprocess.check_output(command)
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

def get_binary_for_spec(spec):
  p = os.path.join('benchspec', 'CPUv6', spec, 'exe')
  newest = max(glob.iglob(p +'/*'), key=os.path.getctime)
  binary = os.path.join(p, newest)
  ts_print(binary)

# MAIN
summary_path = os.path.join(summary_folder, profile)
if not os.path.isdir(summary_path):
  os.makedirs(summary_path)

ts_print('Starting group of tests')


v6 = CpuV6()
# benchmarks = configuration.filter_benchmarks(v6.get_benchmarks())
c = v6.build_config(configuration, profile, flags)

cl = v6.build_command_line(c)
ts_print(cl)
r = run_command(cl)

ts_print('Return code: ' + str(r))

"""
  ts_print('Command result: %u' % proc[0])
  if proc[0] != 0:
    locald[b.name]['times'] = None
    locald[b.name]['size'] = None
    print('runspec command has failed')
    print(proc[1])
  else:
    result = proc[1] 
    save_spec_log(summary_path, profile, b.name, result)

    rsf = None
    time_set = False
    for r in result.split('\n'):
      r = r.strip()
      if r.startswith('format: raw'):
	rsf = r[r.find('/'):].strip()
	ts_print(rsf)
	rsf_result = parse_rsf(rsf)
	locald[b.name]['times'] = rsf_result[0]
	locald[b.name]['error'] = rsf_result[1]
	time_set = True

    # REF results from some reason does not produce .rsf file
    if not time_set:
      results = [float(x.strip().split(' ')[-1]) for x in result.split('\n') if 'Reported:' in x]
      locald[b.name]['times'] = results

    ts_print(locald)

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
"""

"""
with open(dump_file, 'w') as fp:
  json.dump(d, fp, indent = 1)

ts_print(json.dumps(d, indent = 1))
"""
