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
  return r[0]

def negate(flag):
  return '-fno-' + flag[2:]

def get_name(flags):
  return flags.replace(' ', '').replace('-', '_').strip('_')

def generate_config(flags):
  with open('/tmp/config.txt', 'w') as outfile:
    json.dump(map(lambda x: { 'name': get_name(x), 'options': x }, flags), outfile)

o1 = '-fauto-inc-dec -fcompare-elim -fcprop-registers -fdce -fdefer-pop -fdelayed-branch -fdse -fguess-branch-probability -fif-conversion2 -fif-conversion -fipa-pure-const -fipa-profile -fipa-reference -fmerge-constants -fsplit-wide-types -ftree-bit-ccp -ftree-builtin-call-dce -ftree-ccp -fssa-phiopt -ftree-ch -ftree-copyrename -ftree-dce -ftree-dominator-opts -ftree-dse -ftree-forwprop -ftree-fre -ftree-phiprop -ftree-slsr -ftree-sra -ftree-pta -ftree-ter -funit-at-a-time'

o2 = '-fthread-jumps -falign-functions -falign-jumps -falign-loops -falign-labels -fcaller-saves -fcrossjumping -fcse-follow-jumps -fcse-skip-blocks -fdelete-null-pointer-checks -fdevirtualize -fdevirtualize-speculatively -fexpensive-optimizations -fgcse -fgcse-lm -fhoist-adjacent-loads -finline-small-functions -findirect-inlining -fipa-sra -fisolate-erroneous-paths-dereference -foptimize-sibling-calls -fpartial-inlining -fpeephole2 -freorder-blocks -freorder-functions -frerun-cse-after-loop -fsched-interblock -fsched-spec -fschedule-insns -fschedule-insns2 -fstrict-aliasing -fstrict-overflow -ftree-switch-conversion -ftree-tail-merge -ftree-pre -ftree-vrp'

o3 = '-finline-functions -funswitch-loops -fpredictive-commoning -fgcse-after-reload -ftree-loop-vectorize -ftree-slp-vectorize -fvect-cost-model -ftree-partial-pre -fipa-cp-clone'

options = [o1.split(' '), o2.split(' '), o3.split(' ')]

cmd = 'gcc /tmp/abc.c '

flags_collection = []

for i in options[1]:
  flags = '-O2 ' + negate(i)
  flags_collection.append(flags)
  print('%s with result: %u' % (get_name(flags), check_gcc_options(cmd + flags)))

for i in options[2]:
  flags = '-O2 ' + i
  flags_collection.append(flags)
  print('%s with result: %u' % (get_name(flags), check_gcc_options(cmd + flags)))

generate_config(flags_collection)
