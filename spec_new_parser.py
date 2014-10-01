#!/usr/bin/env python

from __future__ import print_function

import os
import sys

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

def strfloat(value, rounding_digits = 2):
  return '%.2f' % round(value, rounding_digits)

### MAIN ###
if len(sys.argv) < 2:
	print('usage: spec_new_parser rootdir profile')
	exit(-1)

rootpath = sys.argv[1]
profilepath = sys.argv[2]

profile_folder = os.path.join(rootpath, 'summary', profilepath)
profiles_file = os.path.join(profile_folder, 'profiles.txt')
profiles = [x.strip() for x in open(profiles_file).readlines()]

d = {}

for profile in profiles:
  d[profile] = {}
  for f in os.listdir(profile_folder):
    if f.startswith(profile + '_') and f.endswith('.log'):
      test = f[len(profile) + 1:-4] 
      report_file = [x for x in open(os.path.join(profile_folder, f)).readlines() if 'format: raw' in x][0].strip()
      report_file = report_file.split(' ')[-1]
      times = [x.strip().split(' ')[-1] for x in open(report_file).readlines() if 'reported_time' in x]
      times = map(lambda x: float(x), filter(lambda x: isfloat(x), times))

      if len(times) > 0:
        avg = sum(times) / len(times)
        d[profile][test] = avg

first = d.keys()[0]
tests = d[first].keys()

p = {}

for (profile, tests) in d.iteritems():
  p[profile] = {}
  for test in tests.keys():
    p[profile][test] = 100 * d[first][test] / d[profile][test]
  values = p[profile].values()

print(':', end = '')
print(':'.join(tests), end = '')
print(':AVG')

for (profile, tests) in p.iteritems():
  print(profile, end = ':')
  print(':'.join(map(lambda x: strfloat(x), tests.values())), end = '')
  avg = sum(tests.values()) / len(tests.values())
  print(':' + strfloat(avg))
