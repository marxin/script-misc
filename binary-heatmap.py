#!/usr/bin/env python3

# Script vizualize heat map of a binary
# Step to run:
# $ perf record -F 10000 -- ./my_binary
# $ perf script -F time,ip,dso > data
# $ ./binary-heatmap.py data gcc10-reorder-heatmap.png cc1plus --title 'GCC 10-reorder'

import argparse
import numpy as np
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description = 'Generate heat map of perf report')
parser.add_argument('perf_stat_file', help = 'Output of perf stat')
parser.add_argument('output_image', help = 'Output image')
parser.add_argument('needle', help = 'Name of the binary in perf stat')
parser.add_argument('--title', help = 'Title')
parser.add_argument('--max-x', help = 'Maximum value on x axis', type = int)
parser.add_argument('--max-y', help = 'Maximum value on y axis', type = int)
args = parser.parse_args()

values = [l.strip() for l in open(args.perf_stat_file).readlines()]

print('Reading perf events for binary name: %s' % args.needle)

x = []
y = []

for value in values:
    parts = [p for p in value.split(' ') if p]

    time = float(parts[0][:-1])
    address = int(parts[1], 16)
    binary = parts[2]

    if args.needle in binary:
        x.append(time)
        y.append(address)
    assert len(parts) == 3

print('Found %d events' % len(x))

first_time = x[0]
for i in range(len(x)):
    x[i] -= first_time

fig, (ax1, ax2) = plt.subplots(1, 2, sharey='row', gridspec_kw={'hspace': 5, 'wspace': 0.05}, figsize=(10, 5))
fig.suptitle(args.title)

ax1.scatter(x, y, s = 0.1, c='green', alpha=0.3, edgecolors='none', marker='s')
ax1.legend()
ax1.grid(True)

ax2.hist(y, 300, orientation='horizontal', color='green')
ax2.set_title('Virtual address histogram')

ax1.set_ylabel('Address')
ax1.set_xlabel('Time')

if args.max_x != None:
    ax1.set_xlim(0, args.max_x)

if args.max_y != None:
    ax1.set_ylim((0, args.max_y))

plt.savefig(args.output_image, dpi = 800)
