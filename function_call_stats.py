#!/usr/bin/env python

from __future__ import print_function

import os
import sys

if len(sys.argv) < 2:
  print('usage: function_call_stats [log_file] {top_entries}')
  exit(-1)

prefix = 'INIT:'
f = sys.argv[1]

call_dictionary = {}

for line in open(f):
  line = line.strip()

  if not line.startswith(prefix):
    continue

  fname = line[len(prefix):]

  if fname in call_dictionary:
    call_dictionary[fname] += 1
  else:
    call_dictionary[fname] = 1

sorted_calls = sorted(call_dictionary.keys(), key = lambda x: call_dictionary[x], reverse = True)
max_calls = call_dictionary[sorted_calls[0]]

print('Maximum number of calls: %s:%u\n' % (sorted_calls[0], max_calls))

histogram = (max_calls + 1) * [0]

for i in call_dictionary:
  histogram[call_dictionary[i]] += 1

if len(sys.argv) >= 3:
  m = min(int(sys.argv[2]), len(sorted_calls))
  print('Top %u occurences:' % m)

  for i in sorted_calls[:m]:
    print('%s:%u' % (i, call_dictionary[i]))

print('\nhistogram:')

for index, value in enumerate(histogram):
  if value > 0:
    print('%3u %u' % (index, value))

# print(call_dictionary)
