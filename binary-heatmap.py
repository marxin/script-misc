#!/usr/bin/env python3

# Script vizualize heat map of a binary
# Step to run:
# Link a program with -Wl,-M,-Map,mapfile.txt,--no-demangle
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
import matplotlib.ticker as ticker
import subprocess
import re
from itertools import chain
from matplotlib.lines import Line2D
from itertools import dropwhile, takewhile

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

def get_symbol_for_sample(symbols, address):
    mid = round(len(symbols) / 2)
    item = symbols[mid]
    a = item['address']
    s = item['size']
    if (a <= address and address < (a + s)):
        return item
    elif len(symbols) == 1:
        return None
    elif address < a:
        return get_symbol_for_sample(symbols[:mid], address)
    else:
        return get_symbol_for_sample(symbols[mid:], address)

def parse_gold_mapfile(filename, sample_addresses):
    text_start = None
    text_unlikely_start = None
    text_startup_start = None
    text_hot_start = None
    text_hot_last = None
    text_end = None

    lines = open(filename).read().splitlines()
    for i, line in enumerate(lines):
        parts = line.split()

        if line.startswith('.text '):
            text_start = int(parts[1], 16)
        elif line.startswith(' .text.unlikely.') and not text_unlikely_start:
            text_unlikely_start = int(lines[i + 1].split()[0], 16)
        elif line.startswith(' .text.startup.') and not text_startup_start:
            text_startup_start = int(lines[i + 1].split()[0], 16)
        elif line.startswith(' .text.hot.'):
            addr = int(lines[i + 1].split()[0], 16)
            if not text_hot_start:
                text_hot_start = addr
            text_hot_end = addr
        elif line.startswith('.fini '):
            text_end = int(parts[1], 16)
            break

    result = []
    c = MapComponent('.text.unlikely', [])
    c.start = text_unlikely_start
    c.end = text_startup_start
    result.append(c)

    c = MapComponent('.text.startup', [])
    c.start = text_startup_start
    c.end = text_hot_start
    result.append(c)

    c = MapComponent('.text.hot', [])
    c.start = text_hot_start
    c.end = text_hot_end
    result.append(c)

    c = MapComponent('.text', [])
    c.start = text_hot_end
    c.end = text_end
    result.append(c)

    return [c.get_address_range() for c in result if c.get_address_range()]

def parse_bfd_mapfile(filename, sample_addresses):
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

    unlikely_symbols = []
    pattern = re.compile(r'\ {16}(0x\w+)\ {16}(.+)')
    for l in components[0].lines:
        m = pattern.match(l)
        if m:
            unlikely_symbols.append({'name': m.group(2), 'address': int(m.group(1), 16)})

    start = 0
    for i, s in enumerate(unlikely_symbols):
        assert s['address'] >= start
        start = s['address']
        if i != len(unlikely_symbols) - 1:
            s['size'] = unlikely_symbols[i + 1]['address'] - s['address']
        else:
            s['size'] = 0

    print('Found %d symbols in .text.unlikely subsection' % len(unlikely_symbols))
    unlikely_accesses = 0
    unlikely_dict = {}
    for address in sample_addresses:
        symbol = get_symbol_for_sample(unlikely_symbols, address)
        if symbol != None:
            if not symbol['name'] in unlikely_dict:
                unlikely_dict[symbol['name']] = 0
            unlikely_dict[symbol['name']] += 1
            unlikely_accesses += 1

    N = 20
    print('Total accessses in .text.unlikely: %d' % unlikely_accesses)
    print('Top %d accessses in .text.unlikely section:' % N)
    for k, v in list(reversed(sorted(unlikely_dict.items(), key = lambda x: x[1])))[:N]:
        print('  %s: %d' % (k, v))

    return [c.get_address_range() for c in components if c.get_address_range()]

def parse_mapfile(filename, sample_addresses):
    if '.note.gnu.gold-version' in open(filename).read():
        print('Parsing ld.gold format mapfile')
        return parse_gold_mapfile(filename, sample_addresses)
    else:
        print('Parsing ld.bfd format mapfile')
        return parse_bfd_mapfile(filename, sample_addresses)

@ticker.FuncFormatter
def major_formatter(x, pos):
    return '%d' % (x / 1024**2)

parser = argparse.ArgumentParser(description = 'Generate heat map of perf report')
parser.add_argument('perf_stat_file', help = 'Output of perf stat')
parser.add_argument('output_image', help = 'Output image')
parser.add_argument('needle', help = 'Name of the binary in perf stat')
parser.add_argument('--title', help = 'Title')
parser.add_argument('--max-x', help = 'Maximum value on x axis', type = int)
parser.add_argument('--max-y', help = 'Maximum value on y axis', type = int)
parser.add_argument('--mapfile', help = 'ld mapfile')
parser.add_argument('--pointsize', help = 'graph point size', type = float, default = 0.2)
parser.add_argument('--pointalpha', help = 'graph point alpha', type = float, default = 0.2)
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
ax1.set_ylabel('Address (in MB)')
ax1.set_xlabel('Time')
ax1.yaxis.set_major_formatter(major_formatter)
ax1.yaxis.set_major_locator(ticker.MultipleLocator(2 * 1024**2))
ax1.set_title('Executed instruction address')

ax2.hist(y, 300, orientation='horizontal', color='green')
ax2.set_title('Virtual address histogram')
ax2.set_xlabel('Sample count')

if args.max_x:
    ax1.set_xlim(0, args.max_x)

if args.max_y:
    ax1.set_ylim((0, args.max_y))

if args.mapfile:
    ranges = parse_mapfile(args.mapfile, y)

    colors = 'cmrkby'
    custom_lines = []
    print('Found ELF .text subsections: %s' % str(ranges))
    alpha = .1
    for i, r in enumerate(ranges):
        samples = len([a for a in y if r[1] <= a and a <= r[2]])
        fraction = (100.0 * samples / len(x))
        size = 1.0 * (r[2] - r[1]) / (1024**2)
        custom_lines.append(Line2D([0], [0], color=colors[i], alpha=0.1, lw=4, label= r[0] + ' (size: %.2f MB; samples: %d (%.2f%%))' % (size, samples, fraction)))
        ax1.axhspan(r[1], r[2], facecolor=colors[i], alpha=alpha)
        ax2.axhspan(r[1], r[2], facecolor=colors[i], alpha=alpha)
    fig.legend(handles=list(reversed(custom_lines)), loc = 'upper left', prop={'size': 6})

plt.savefig(args.output_image, dpi = 800)
