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

# TODO
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
class SpecConfiguration:
    def build_config(self, configuration, profile, flags, template_name):
        config_template_path = os.path.join(real_script_folder, 'config-template', template_name)
        compilers = configuration.compilers()
        lines = [x.strip() for x in open(config_template_path, 'r').readlines()]

        new_lines = []
        for line in lines:
            if line == 'JOBS_PLACEHOLDER':
                new_lines.append('makeflags = -j' + str(cpu_count()))
            elif line == 'OPTIMIZE_PLACEHOLDER':
                new_lines.append('OPTIMIZE = ' + flags)
                if args.compiler == 'icc':
                    new_lines.append('COPTIMIZE = ' + flags + ' -std=gnu11')
            elif line == 'COMPILERS_PLACEHOLDER':
                new_lines.append('FC = ' + compilers['FC'])
                new_lines.append('CXX = ' + compilers['CXX'])
                new_lines.append('CC = ' + compilers['CC'])
                new_lines.append('EXTRA_LDFLAGS = ' + compilers['LD'])
            else:
                new_lines.append(line)

        config_filename = profile + '.cfg'
        config_path = os.path.join(config_folder, config_filename)
        if not os.path.exists(config_folder):
            os.makedirs(config_folder)

        f = open(config_path, 'w')
        f.write('\n'.join(new_lines))

        ts_print('generating config to: ' + config_path)
        return config_filename


class CpuV6(SpecConfiguration):
    def build_command_line(self, c):
        all_tests = sorted('557.xz_r 500.perlbench_r 525.x264_r 544.nab_r 553.johnripper_r 505.mcf_r 547.drops_r 502.gcc_r 523.xalancbmk_r 508.namd_r 549.fotonik3d_r 503.bwaves_r 510.parest_r 548.exchange2_r 531.deepsjeng_r 513.hmmer_r 526.blender_r 552.mdwp_r 532.facesim_r 511.povray_r 556.ferret_r 519.lbm_r 539.bodytrack_r 520.omnetpp_r 507.cactuBSSN_r 527.cam4_r 521.wrf_r 538.imagick_r 541.leela_r 554.roms_r'.split(' '))
        slow_tests = set(['bwaves', 'wrf', 'roms'])
        tests = list(filter(lambda x: not any(map(lambda y: y in x, slow_tests)), all_tests))
        ts_print('Running tests: %d' % len(tests))

        # TODO
        tests = tests[-1:]
        return runspec_command('--config=' + c + ' --output-format=raw ' + runspec_arguments + ' '.join(tests))

class Cpu2006(SpecConfiguration):
    def build_command_line(self, c):
        tests = sorted('400.perlbench 401.bzip2 403.gcc 429.mcf 445.gobmk 456.hmmer 458.sjeng 462.libquantum 464.h264ref 471.omnetpp 473.astar 483.xalancbmk 999.specrand 410.bwaves 416.gamess 433.milc 434.zeusmp 435.gromacs 436.cactusADM 437.leslie3d 444.namd 447.dealII 450.soplex 453.povray 454.calculix 459.GemsFDTD 465.tonto 470.lbm 481.wrf 482.sphinx3'.split(' '))
        tests = tests[-1:]
        return runspec_command('--config=' + c + ' --output-format=raw ' + runspec_arguments + ' '.join(tests))

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

# TODO
suite = None
config = None

if args.root_path.endswith('cpuv6'):
    suite = CpuV6()
    config = suite.build_config(configuration, profile, flags, 'config-template-v6.cfg')
else:
    suite = Cpu2006()
    config = suite.build_config(configuration, profile, flags, 'config-template.cfg')

run_command(runspec_command(' --action trash --config=' + config + ' all'))
cl = suite.build_command_line(config)
ts_print(cl)
r = run_command(cl)

ts_print('Return code: ' + str(r))
