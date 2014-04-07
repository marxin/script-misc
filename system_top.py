#!/usr/bin/env python

from __future__ import print_function
from time import time

import os
import sys
import time
import getopt
import re
import subprocess

vmstat_temp = '/tmp/vmstat.log'

class Process:
  def __init__(self, pid, name, args):
    self.pid = int(pid)
    self.name = name
    self.args = args
    self.memory = []
    self.nick = ''

  def __eq__(self, other):
    return self.pid == other.pid

  def __hash__(self):
    return self.pid

  def __repr__(self):
    return "<Process %s:%u [%u]>" % (self.nick, self.pid, len(self.memory))

  def report_memory(self, time, memory):
    self.memory.append((time, memory))
    print('%s:%f:%u' % (self.nick, time, memory))

processes = []

def get_process_nickname_if_monitored(p):
  if p in processes:
    return None

  # ld -plugin
  if p.name.endswith('/ld') and len(p.args) and p.args[0] == '-plugin':
    return 'ld'

  # WPA lto1
  lto1wpa = 'lto1_WPA'
  if p.name.endswith('lto1') and any(map(lambda x: x.endswith('.wpa'), p.args)) and all(map(lambda x: x.nick != lto1wpa, processes)):
    return lto1wpa

  # LTRANS lto1
  if p.name.endswith('lto1') and any(map(lambda x: re.match('.*ltrans[0-9].*', x), p.args)):
    ltrans_arg = next(x for x in p.args if 'ltrans' in x)
    return 'lto1_' + ltrans_arg

  return None

def print_cpu():
  vmstat_line = os.popen('tail -n1 ' + vmstat_temp).readlines()[0].strip()
  tokens = [x for x in vmstat_line.split() if x]  
  print('CPU:%f:%u' % (time.time(), min(100, int(tokens[12]) + int(tokens[13]) + int(tokens[15]))))

def print_ram():
  r = os.popen('free | head -n3 | tail -n1 | tr -s " " |cut -f3 -d" "').readlines()[0].strip()
  print('RAM:%f:%s' % (time.time(), r))

def main():
  args = sys.argv[1:]
  optlist, args = getopt.getopt(args, 't:')

  # start vmstat period
  pid = os.fork()
  if pid == 0:
    os.system('vmstat -n 1 1111111 >> ' + vmstat_temp)
  else:
    while True:
      ps = os.popen('ps v').readlines()[1:]
      t = time.time()

      # consumption map
      consumption = {}

      # iterate for new process
      for line in ps:
	tokens = [x.strip() for x  in line.split(' ') if x]
	p = Process(tokens[0], tokens[9], tokens[10:])

	consumption[p.pid] = int(tokens[7])
	nick = get_process_nickname_if_monitored(p)

	if nick != None:
	  p.nick = nick
	  processes.append(p)

      # add memory consumption for all monitored processes
      for p in processes:
	if p.pid in consumption:
	  p.report_memory(t, consumption[p.pid])

      # CPU & MEM
      print_cpu()
      print_ram()

      interval = 900
      time.sleep(interval / 1000.0)

### MAIN ###
try:
  main()
except KeyboardInterrupt:
  sys.exit(0)
