#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import datetime
import shutil
import commands
import json

def check_gcc_options(cmd):
  r = commands.getstatusoutput(cmd)
#  if r[0] != 0:
#    print(r[1])
  return r[0]

def negate(flag):
  return '-fno-' + flag[2:]

def get_name(flags):
  return flags.replace(' ', '').replace('-', '_').strip('_')

def generate_config(flags):
  with open('/tmp/config.txt', 'w') as outfile:
    json.dump(map(lambda x: { 'name': get_name(x), 'options': x }, flags), outfile)

def diff(source, subset):
  return [x for x in source if not x in subset]

def get_options_ending_with(string, cmd = ''):
  lines = [x for x in commands.getstatusoutput('gcc -Q --help=optimizers ' + cmd)[1].split('\n') if x.strip().endswith(string)]
  return map(lambda x: x.split('\t')[0].strip(), lines)

def get_options_by_compiler():
  all_options = get_options_ending_with('bled]')
  o0 = get_options_ending_with('enabled]', '-O0')
  o1 = diff(get_options_ending_with('enabled]', '-O1'), o0)
  o2 = diff(get_options_ending_with('enabled]', '-O2'), o0 + o1)
  o3 = diff(get_options_ending_with('enabled]', '-O3'), o0 + o1 + o2)
  o4 = diff(all_options, o0 + o1 + o2 + o3)

  gcc_options = [o1, o2, o3, o4]
  return gcc_options

def test_and_add(flags, l):
  r = check_gcc_options(cmd + flags)

  if r == 0:
    l.append(flags)
  print('%s with result: %u' % (get_name(flags), r))

o1 = '-fauto-inc-dec -fcompare-elim -fcprop-registers -fdce -fdefer-pop -fdelayed-branch -fdse -fguess-branch-probability -fif-conversion2 -fif-conversion -fipa-pure-const -fipa-profile -fipa-reference -fmerge-constants -fsplit-wide-types -ftree-bit-ccp -ftree-builtin-call-dce -ftree-ccp -fssa-phiopt -ftree-ch -ftree-copyrename -ftree-dce -ftree-dominator-opts -ftree-dse -ftree-forwprop -ftree-fre -ftree-phiprop -ftree-slsr -ftree-sra -ftree-pta -ftree-ter -funit-at-a-time'

o2 = '-fthread-jumps -falign-functions -falign-jumps -falign-loops -falign-labels -fcaller-saves -fcrossjumping -fcse-follow-jumps -fcse-skip-blocks -fdelete-null-pointer-checks -fdevirtualize -fdevirtualize-speculatively -fexpensive-optimizations -fgcse -fgcse-lm -fhoist-adjacent-loads -finline-small-functions -findirect-inlining -fipa-sra -fisolate-erroneous-paths-dereference -foptimize-sibling-calls -fpartial-inlining -fpeephole2 -freorder-blocks -freorder-functions -frerun-cse-after-loop -fsched-interblock -fsched-spec -fschedule-insns -fschedule-insns2 -fstrict-aliasing -fstrict-overflow -ftree-switch-conversion -ftree-tail-merge -ftree-pre -ftree-vrp'

o3 = '-finline-functions -funswitch-loops -fpredictive-commoning -fgcse-after-reload -ftree-loop-vectorize -ftree-slp-vectorize -fvect-cost-model -ftree-partial-pre -fipa-cp-clone'

options = [o1.split(' '), o2.split(' '), o3.split(' ')]
gcc_options = get_options_by_compiler()

for (i, level) in enumerate(gcc_options[:3]):
  for optimization in level:
    if not optimization in options[i]:
      print('missing in O%u: %s' % (i + 1, optimization))

cmd = 'gcc /tmp/abc.c '

flags_collection = []

test_and_add('-Os', flags_collection)
test_and_add('-O1', flags_collection)
test_and_add('-O2', flags_collection)
test_and_add('-O3', flags_collection)
test_and_add('-Ofast', flags_collection)

for i in gcc_options[1]:
  flags = '-O2 ' + negate(i)
  test_and_add(flags, flags_collection)

for i in gcc_options[2]:
  flags = '-O2 ' + i
  test_and_add(flags, flags_collection)

for i in gcc_options[3]:
  flags = '-O2 ' + i
  test_and_add(flags, flags_collection)

generate_config(flags_collection)
