#!/usr/bin/env python3

# Script vizualize heat map of a binary
# Step to run:
# $ perf record -F 10000 -- ./my_binary
# $ perf script -F time,ip,dso > data
# $ ./binary-heatmap.py data gcc10-reorder-heatmap.png cc1plus --title 'GCC 10-reorder'
#
# Sample of perf script file:
# 2415.281677:            e18b08 (/tmp/gcc10-cc1plus)
# 2415.281763:            e35e7f (/tmp/gcc10-cc1plus)
# 2415.281857:            dee2fd (/tmp/gcc10-cc1plus)

import argparse
import numpy as np
import matplotlib.pyplot as plt
import subprocess
from itertools import chain
from matplotlib.lines import Line2D

class SectionPlaceholder:
    def __init__(self, line):
        parts = [l for l in line.split(' ') if l]
        self.address = int(parts[0], 16)
        parts = parts[2].split('_')
        self.name = parts[-2]
        self.start = parts[-1] == 'start'

    def get_range(self, placeholders):
        if self.start:
            for p in placeholders:
                if self.name == p.name and not p.start and self.address != p.address:
                    return (self.name, self.address, p.address)
        return None

parser = argparse.ArgumentParser(description = 'Generate heat map of perf report')
parser.add_argument('perf_stat_file', help = 'Output of perf stat')
parser.add_argument('output_image', help = 'Output image')
parser.add_argument('needle', help = 'Name of the binary in perf stat')
parser.add_argument('--title', help = 'Title')
parser.add_argument('--max-x', help = 'Maximum value on x axis', type = int)
parser.add_argument('--max-y', help = 'Maximum value on y axis', type = int)
parser.add_argument('--binary', help = 'Path to binary')
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
ax1.grid(True, linewidth = 0.5, alpha = 0.3)

ax2.hist(y, 300, orientation='horizontal', color='green')
ax2.set_title('Virtual address histogram')

ax1.set_ylabel('Address')
ax1.set_xlabel('Time')

if args.max_x:
    ax1.set_xlim(0, args.max_x)

if args.max_y:
    ax1.set_ylim((0, args.max_y))

if args.binary:
    r = subprocess.check_output('nm ' + args.binary, shell = True, encoding = 'utf8')
    symbols = [SectionPlaceholder(l) for l in r.split('\n') if '__text_' in l]
    ranges = [s.get_range(symbols) for s in symbols]
    ranges = sorted([r for r in ranges if r], key = lambda x: x[0])

    colors = 'brcmyk'
    custom_lines = []
    print('Found ELF .text subsections: %s' % str(ranges))
    alpha = .1
    for i, r in enumerate(ranges):
        samples = len([a for a in y if r[1] <= a and a <= r[2]])
        fraction = (100.0 * samples / len(x))
        size = 1.0 * (r[2] - r[1]) / (1024**2)
        custom_lines.append(Line2D([0], [0], color=colors[i], alpha=alpha, lw=4, label= '.text.' + r[0] + ' (size: %.2f MB; samples: %.2f%%)' % (size, fraction)))
        ax1.axhspan(r[1], r[2], facecolor=colors[i], alpha=alpha)
    fig.legend(handles=custom_lines, loc = 'upper left', prop={'size': 6})

plt.savefig(args.output_image, dpi = 800)
