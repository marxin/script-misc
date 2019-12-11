#!/usr/bin/env python3

# Script vizualize heat map of a binary
# Step to run:
# Link a program with -Wl,-M,-Map,mapfile.txt
# That will create a .text subsection map file that can be later used
# for visualization of a binary
# $ perf record -F 10000 -- ./my_binary
# $ perf script -F time,ip,dso > data
# $ ./binary-heatmap.py data gcc10-reorder-heatmap.png cc1plus --title 'GCC 10-reorder' --mapfile mapfile.txt
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
from itertools import dropwhile, takewhile

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

class MapComponent:
    def __init__(self, name, lines):
        self.name = name
        self.lines = lines[1:]
        self.addresses = []
        self.start = None
        self.end = None

        for l in self.lines:
            parts = [x for x in l.split(' ') if x]
            if len(parts) >= 1 and parts[0].startswith('0x0'):
                self.addresses.append(int(parts[0], 16))

    def get_address_range(self):
        if self.start and self.end and self.name and self.start != self.end:
            return (self.name, self.start, self.end)
        else:
            return None

def parse_mapfile(filename):
    components = []
    map_components = [
        (' *(.text.unlikely .text.*_unlikely .text.unlikely.*)', '.text.unlikely'),
        (' *(.text.exit .text.exit.*)', '.text.exit'),
        (' *(.text.startup .text.startup.*)', '.text.startup'),
        (' *(.text.hot .text.hot.*)', '.text.hot'),
        (' *(SORT_BY_NAME(.text.sorted.*))', '.text.sorted'),
        (' *(.text .stub .text.* .gnu.linkonce.t.*)', '.text.normal'),
        (' *(.gnu.warning)', None),
        ('.gnu.attributes', None)
    ]

    lines = [l.rstrip() for l in open(filename)]

    # filter map_components to existing one
    map_components = [mc for mc in map_components if mc[0] in lines]

    lines = list(dropwhile(lambda x: x != map_components[0][0], lines))
    for i in range(0, len(map_components) - 1):
        chunk = list(takewhile(lambda x: x != map_components[i+1][0], lines))
        components.append(MapComponent(map_components[i][1], chunk))
        lines = lines[len(chunk):]

    components[-1].start = components[-1].addresses[0]
    end = components[-1].start

    for i in reversed(range(len(map_components) - 1)):
        components[i].end = end
        if len(components[i].addresses):
            components[i].start = components[i].addresses[0]
            end = components[i].start

    return [c.get_address_range() for c in components if c.get_address_range()]


parser = argparse.ArgumentParser(description = 'Generate heat map of perf report')
parser.add_argument('perf_stat_file', help = 'Output of perf stat')
parser.add_argument('output_image', help = 'Output image')
parser.add_argument('needle', help = 'Name of the binary in perf stat')
parser.add_argument('--title', help = 'Title')
parser.add_argument('--max-x', help = 'Maximum value on x axis', type = int)
parser.add_argument('--max-y', help = 'Maximum value on y axis', type = int)
parser.add_argument('--mapfile', help = 'ld mapfile')
parser.add_argument('--pointsize', help = 'graph point size', type = float, default = 0.2)
parser.add_argument('--pointalpha', help = 'graph point alpha', type = float, default = 0.4)
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
if len(x) == 0:
    print('Error: no events')
    exit(1)

first_time = x[0]
for i in range(len(x)):
    x[i] -= first_time

fig, (ax1, ax2) = plt.subplots(1, 2, sharey='row', gridspec_kw={'hspace': 5, 'wspace': 0.05}, figsize=(10, 5))
fig.suptitle(args.title)

ax1.scatter(x, y, s = args.pointsize, c='green', alpha=args.pointalpha, edgecolors='none', marker='s')
ax1.grid(True, linewidth = 0.5, alpha = 0.3)
ax1.set_ylabel('Address')
ax1.set_xlabel('Time')

ax2.hist(y, 300, orientation='horizontal', color='green')
ax2.set_title('Virtual address histogram')
ax2.set_ylabel('Address')
ax2.set_xlabel('Sample count')

if args.max_x:
    ax1.set_xlim(0, args.max_x)

if args.max_y:
    ax1.set_ylim((0, args.max_y))

if args.mapfile:
    ranges = parse_mapfile(args.mapfile)

    colors = 'cmrkby'
    custom_lines = []
    print('Found ELF .text subsections: %s' % str(ranges))
    alpha = .1
    for i, r in enumerate(ranges):
        samples = len([a for a in y if r[1] <= a and a <= r[2]])
        fraction = (100.0 * samples / len(x))
        size = 1.0 * (r[2] - r[1]) / (1024**2)
        custom_lines.append(Line2D([0], [0], color=colors[i], alpha=0.1, lw=4, label= r[0] + ' (size: %.2f MB; samples: %.2f%%)' % (size, fraction)))
        ax1.axhspan(r[1], r[2], facecolor=colors[i], alpha=alpha)
        ax2.axhspan(r[1], r[2], facecolor=colors[i], alpha=alpha)
    fig.legend(handles=list(reversed(custom_lines)), loc = 'upper left', prop={'size': 6})

plt.savefig(args.output_image, dpi = 800)
