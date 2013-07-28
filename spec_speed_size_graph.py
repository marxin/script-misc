#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

plt.rc('text', usetex = True)
font = {'family' : 'serif', 'size':13}
plt.rc('font',**font)
plt.rc('legend',**{'fontsize':11})

profiles = ['LTO 02', 'UG5', 'UG10', 'UG15', 'UG20', 'UG25', 'UG30', 'LTO O3']
times = [49.926026, 48.079934, 47.952832, 48.545109, 47.622540, 45.598985, 44.856360, 44.895013]
sizes = [4419672, 4316957, 4374225, 4442979, 4515759, 4592449, 4661235, 4661235]

base_time = times[0]
base_size = sizes[0]

times_percentage = [100.0 * base_time / x for x in times]
sizes_percentage = [100.0 * x / base_size for x in sizes]

x = range(0, len(profiles))

boundary = 0.5

plt.rcParams['figure.figsize'] = 10, 5
fig = plt.figure()
ax = plt.subplot(111)

ax.plot(times_percentage, 'y--s', markersize = 10, label = 'Speedup')
ax.plot(sizes_percentage, 'g--o', markersize = 10, label = 'Size growth')
plt.xticks(x, profiles)
plt.xlim((-boundary, len(profiles) - 1 + boundary))
plt.ylim((80, 120))
plt.grid(True)

ax.set_ylabel('\%')
ax.legend()

plt.tight_layout()
plt.savefig('/tmp/data.pdf')
