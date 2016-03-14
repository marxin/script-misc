#!/usr/bin/env python

from __future__ import print_function
from optparse import OptionParser

import os
import sys
import fnmatch
import datetime
import string
import numpy as np

def my_map(func, list):
  result = []

  for (i, v) in enumerate(list):
    result.append(func(i, v))

  return result

def padd(value, width, direction):
  if direction == 'l':
    return value.ljust(width)
  else:
    return value.rjust(width)

def format_line(line, separator = '|'):
  return separator + string.join(my_map(lambda i, x: padd(x, column_width_array[i], column_padding_array[i]), line), separator) + separator

def print_sep():
  sep = format_line(map(lambda x: '-' * x, column_width_array), '+')
  print(sep)

def print_super_line(line):
  if not line:
    return

  print_sep()
  print(format_line(line))
  print_sep()

parser = OptionParser()
parser.add_option("-d", "--delimiter", dest="delimiter", help="column delimiter", default = ';')
parser.add_option("-f", "--file", dest="file", help="input file")
parser.add_option("-a", "--default-padding", dest="default_padding", help="default padding in format {l|r}", default = 'l')
parser.add_option("-p", "--padding", dest="padding", help="padding in format [column]|[column_range]{l|r}")
parser.add_option("-e", "--header", dest="header", action="store_true", help="first line is header")
parser.add_option("-o", "--footer", dest="footer", action="store_true", help="last line is footer")
parser.add_option("-t", "--transpose", dest="transpose", action="store_true", help="changes rows and columns")
parser.add_option("-n", "--number", dest="number", action="store_true", help="number lines")

(options, args) = parser.parse_args()

lines = [map(lambda y: ' ' + y + ' ', [z for z in x.strip().split(options.delimiter) if z != '']) for x in open(options.file).readlines()]

if options.transpose:
  h = len(lines)
  w = len(lines[0])

  new_lines = []
  for i in range(w):
    new_lines.append([None] * h)

  for x, y in np.ndindex((w, h)):
    new_lines[x][y] = lines[y][x]

  lines = new_lines

if options.number:
    for (i, v) in enumerate(lines):
        v.insert(0, str(i + 1))

columns = len(lines[0])
column_width_array = [0] * columns
column_padding_array = [options.default_padding] * columns

if options.padding:
  for token in options.padding.split(','):
    direction = token[-1]
    token = token[:-1]
    if '-' in token:
      values = token.split('-')
      for i in range(int(values[0]) - 1, int(values[1]) - 1):
	if i >= len(column_padding_array):
	  continue
	column_padding_array[i] = direction
    else:
      i = int(token)
      if i >= len(column_padding_array):
	continue
      column_padding_array[i] = direction

for line in lines:
  for (i, column) in enumerate(line):
    if len(column) > column_width_array[i]:
      column_width_array[i] = len(column)

first_line = None
last_line = None

if options.header:
  first_line = lines[0]
  lines = lines[1:]
  print_super_line(first_line)
else:
  print_sep()

print_bottom_line = False

if options.footer:
  last_line = lines[-1]
  lines = lines[:-1]
else:
  print_bottom_line = True

for line in lines:
  print(format_line(line))

if print_bottom_line:
  print_sep()
