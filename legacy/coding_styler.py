#!/usr/bin/env python

import os
import sys
import subprocess
import commands
import shutil
import datetime
import multiprocessing
import signal
import re
import argparse
import itertools

def relative_path(root, full_path):
  subpath = full_path[len(os.path.commonprefix([root, full_path])):]
  return subpath

def check_leading_whitespaces(line, tab_width):
  leading = ''.join(itertools.takewhile(lambda x: x == ' ' or x == '\t', line))
  tokens = leading.split('\t')
  f = filter(lambda x: len(x) > 0, tokens)

  if len(f) > 1:
    return False

  return all(map(lambda x: len(x) < tab_width, tokens))

def analyze_ends_with_whitespace (lines):
  return map(lambda x: (x[0] + 1, 'WS %u :%s' % (x[0] + 1, x[1])), filter(lambda x: x[1].rstrip() != x[1], enumerate(lines)))

def analyze_leading_whitespaces (lines, tab_width):
  return map(lambda x: (x[0] + 1, 'LWS %u :%s' % (x[0] + 1, x[1])), filter(lambda x: not check_leading_whitespaces(x[1], tab_width), enumerate(lines)))

def analyze_line_length (lines, limit):
  return map(lambda x: (x[0] + 1, 'LL %u (%u):%s' % (x[0] + 1, len(x[1]), x[1])), filter(lambda x: len(x[1]) > limit, enumerate(lines)))

def analyze_file(file, options, modified):
  if modified != None and not file in modified:
    return

  lines = map(lambda x: x.rstrip('\n'), open(file).readlines())
  problems = analyze_line_length (lines, options.line_limit)
  problems.extend(analyze_ends_with_whitespace(lines))
  problems.extend(analyze_leading_whitespaces(lines, options.tab_width))

  if modified != None:
    changed_lines = modified[file]
    problems = filter(lambda x: x[0] in changed_lines, problems)

  if len(problems) > 0:
    print(file)

  for l in problems:
    print(l[1])

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--folder", dest="folder", help="Source base folder")
parser.add_argument("-d", "--diff", dest="diff", help="Git diff file")
parser.add_argument("-i", "--ignore", dest="ignore", type = str, help="Ignore pattern", default = ['.*testsuite/.*'], nargs='+')
parser.add_argument("-e", "--extensions", dest="extensions", type = str, help="File extensions", default = ['h', 'c'], nargs='+')
parser.add_argument("-ll", "--line-limit", dest="line_limit", type = int, help="Line limit", default = 80)
parser.add_argument("-tw", "--tab-width", dest="tab_width", type = int, help="Tab width", default = 8)

options = parser.parse_args()

if not options.folder:
  parser.error('folder not specified')

modified = None
if options.diff != None:
  lines = [x.strip() for x in open(options.diff).readlines()]

  last_file = ''
  modified = {}

  for (i, v) in enumerate(lines):
    if v.startswith('diff'):
      last_file = os.path.join(options.folder, v.split(' ')[-1][2:])
      if not last_file in modified:
	modified[last_file] = []
    elif v.startswith('@@'):      
      x = v.split(' ')[2][1:]
      if ',' in x:
	tokens = [int(y) for y in x.split(',')]
	modified[last_file].extend(range(tokens[0], tokens[0] + tokens[1]))
      else:
	modified[last_file].append(int(x))

for root, dirs, files in os.walk(options.folder):
  for f in files:
    if not os.path.splitext(f)[1][1:] in options.extensions:
      continue

    full_path = os.path.join(root, f)
    rel = relative_path (options.folder, full_path)
    if any(map(lambda x: re.match(x, rel) != None, options.ignore)):
      continue

    analyze_file(full_path, options, modified)
