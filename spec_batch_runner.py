#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import datetime
import shutil

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

root_path = '/home/marxin/Programming/cpu2006/'
profile_path = '/tmp/spec2006'

config_folder = os.path.join(root_path, 'config')
summary_folder = os.path.join(root_path, 'summary')
config_template = os.path.join(config_folder, 'config-template.cfg')

default_flags = '-fno-strict-aliasing -fpeel-loops -ffast-math -march=native'
# runspec_arguments = '--size=train --no-reportable --iterations=3 '
profile_arguments = '--size=test --no-reportable --iterations=1 '
runspec_arguments = '--size=test --no-reportable --iterations=1 '


profiles =  [
              [
                'gcc-O2-lto-ipa-icf',
		'',
                '-O2 -flto -fdump-ipa-icf-details',
                False
              ],
"""	      
              [
                'gcc-O2-lto-no-ipa-icf',
		'',
		'-O2 -flto -fno-ipa-icf -Wl,--icf=all,--print-icf-sections -ffunction-sections',
                False
              ]
"""
	]

if len(sys.argv) < 2:
  print('usage: [test_prefix]')
  uxit(-1)

test_prefix = sys.argv[1]

def full_profile_name(name):
  return test_prefix + '_' + name

def generate_config(profile, extra_flags = ''):
  lines = open(config_template, 'r').readlines()

  p = 94

  flags = default_flags + ' ' + profile[2] + ' ' + extra_flags

  lines.insert(p, 'FOPTIMIZE = ' + flags)
  lines.insert(p, 'CXXOPTIMIZE= ' + flags)
  lines.insert(p, 'COPTIMIZE= ' + flags)

  p = 54

  lines.insert(p, 'FC = ' + os.path.join(profile[1], 'gfortran'))
  lines.insert(p, 'CXX = ' + os.path.join(profile[1], 'g++'))
  lines.insert(p, 'CC = ' + os.path.join(profile[1], 'gcc'))

  p = 36

  lines.insert(p, 'ext = ' + full_profile_name(profile[0]))

  config_name = os.path.join(config_folder, full_profile_name(profile[0]))
  f = open(config_name, 'w+')

  for l in lines:
    f.write(l.strip() + '\n')

  return config_name

def save_spec_log(folder, profile, benchmark, data):
  f = open(os.path.join(folder, profile + '_' + benchmark + '.log'), 'w+')

  for l in data:
    f.write(l)

def parse_csv(path, folder, profile):
  d = {}

  for line in open(path, 'r'):
    tokens = line.split(',')

    if line.startswith('"Selected Results Table"'):
      break

    if line.startswith('4') and len(tokens) >= 12 and len(tokens[2]) > 0:
      test = tokens[0]
      if test in d:
        d[test].append(float(tokens[2]))
      else:
        d[test] = [float(tokens[2])]

  f = open(os.path.join(folder, profile + '-time.csv'), 'a+')

  for k in d.keys():
    total = 0

    for i in d[k]:
      total += i

    f.write('%s:%f\n' % (k, total / len(d[k])))

  f.close()

def parse_binary_size(folder, profile, benchmark):
  pn = full_profile_name(profile)

  subfolder = os.path.join(root_path, 'benchspec/CPU2006', benchmark, 'exe')

  size = 0

  for exe in os.listdir(subfolder):
    if exe.endswith(pn):
      size = int(os.path.getsize(os.path.join(subfolder, exe)))

  f = open(os.path.join(folder, profile + '-size.csv'), 'a+')
  f.write('%s:%u\n' % (benchmark, size))
  f.close()

def ts_print(*args):
  print('[%s]: ' % datetime.datetime.now(), end = '')

  for a in args:
    print(a)

def get_benchmark_name(benchmark):
  return benchmark[0].split('.')[1]

def clear_tmp():
  if os.path.exists(profile_path):
    shutil.rmtree(profile_path)

# MAIN

summary_path = os.path.join(summary_folder, test_prefix)
if not os.path.isdir(summary_path):
  os.mkdir(summary_path)

ts_print('Starting group of tests')

for i, profile in enumerate(profiles[-2:]):
  ts_print('Running %u/%u: %s' % (i + 1, len(profiles), profile[0]))

  pgo = profile[3]

  for j, benchmark in enumerate(benchmarks):
    clear_tmp()

    if len(profile) == 5 and benchmark[0] in profile[4]:
      ts_print('Skipping benchmark: ' + benchmark[0])
      continue

    ts_print('Running subphase: %u/%u: %s' % (j + 1, len(benchmarks), benchmark[0]))

    # Profile generate phase
    if pgo:
      ts_print('Profile generate phase')
      c = generate_config(profile, '-fprofile-generate=' + profile_path)
      cl = 'runspec --output_format=csv --config=' + c + ' ' + profile_arguments + get_benchmark_name(benchmark)
      ts_print(cl)
      result = os.popen(cl).readlines()

    # Real benchmark run
    extra = ''

    if pgo:
      ts_print('Profile use phase')
      extra = '-fprofile-use=' + profile_path

    c = generate_config(profile, extra)

    cl = 'runspec --config=' + c + ' ' + runspec_arguments + get_benchmark_name(benchmark)
    ts_print(cl)
    result = os.popen(cl).readlines()
    save_spec_log(summary_path, profile[0], get_benchmark_name(benchmark), result)

    csv = ''
    for r in result:
      r = r.strip()
      print(r, file = sys.stderr)
      if r.startswith('format: CSV'):
        csv = r[r.find('/'):].strip()

    # parse_csv(csv, summary_path, profile[0])
    parse_binary_size(summary_path, profile[0], benchmark[0])

  ts_print('Finishing %u/%u: %s' % (i + 1, len(profiles), profile[0]))
