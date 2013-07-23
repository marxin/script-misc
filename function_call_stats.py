#!/usr/bin/env python

from __future__ import print_function
from pylab import *
import numpy as np
import matplotlib.pyplot as plt

import os
import sys
import math

plt.rc('text', usetex = True)
font = {'family' : 'serif', 'size':14}
plt.rc('font', **font)
plt.rc('legend',**{'fontsize': 14})

if len(sys.argv) < 2:
  print('usage: function_call_stats [log_file] {top_entries}')
  exit(-1)

prefix = 'INIT:'
f = sys.argv[1]

call_dictionary = {}

i = 0
print('Loading:', end = '')

for line in open(f):
  i += 1

  if i % (1000 * 1000) == 0:
    print ('.', end = '')
    sys.stdout.flush()

  fname = line.strip()

  if fname.startswith(prefix):
    fname = fname[len(prefix):]

  if fname in call_dictionary:
    call_dictionary[fname] += 1
  else:
    call_dictionary[fname] = 1

print()

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

# histogram creation
histogram_keys = []
histogram_values = []

for i in range(1, 10):
  histogram_keys.append(str(i))
  histogram_values.append(histogram[i])

maxlog = 8
buckets = [0] * maxlog

for index, value in enumerate(histogram):
  if index == 0:
    continue

  b = int(math.log10(index)) + 1
  buckets[b] += value

histogram_values += buckets[2:]

for i in range(2, maxlog):
  histogram_keys.append('$\\alpha$=%u' % i)

print(histogram_keys)
print(histogram_values)
print(buckets)

# graph
width = 8

plt.rcParams['figure.figsize'] = 10, 6
fig = plt.figure()
ax = fig.add_subplot(111)
ax.set_title('Histogram of function call frequency')

text(0.05, 0.95, 'NOTE: $\\alpha=n$ denotes interval $[10^{n-1};10^n)$', horizontalalignment = 'left', verticalalignment = 'center', transform = ax.transAxes, bbox = {'facecolor':'orange', 'pad':10, 'alpha': 0.4})

x = np.arange(len(histogram_keys)) + width / 2
rects = ax.bar(x, histogram_values, width, color = 'y')

"""
data2 = [2064, 1817, 814, 978, 511, 673, 382, 516, 285, 7109, 4792, 1976, 523, 97, 1]
rects2 = ax.bar(x + width, data2, width, color = 'r')
ax.legend((rects[0], rects2[0]), ('All Firefox libraries', '\\texttt{libxul.so} library') )
"""

xticks(x + width / 2, histogram_keys)
xlabel('Number of function calls')
ylabel('Function count')

tight_layout(1.5)
savefig('/tmp/call-histogram.pdf')

# print(call_dictionary)
