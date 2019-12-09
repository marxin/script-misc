#!/usr/bin/env python3

import argparse
import numpy as np
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description = 'Generate heat map of perf report')
parser.add_argument('perf_stat_file', help = 'Output of perf stat')
parser.add_argument('output_image', help = 'Output image')
parser.add_argument('--title', help = 'Title')
args = parser.parse_args()

values = [l.strip() for l in open(args.perf_stat_file).readlines()]

x = []
y = []

for value in values:
    parts = [p for p in value.split(' ') if p]

    time = float(parts[0][:-1])
    address = int(parts[1], 16)
    binary = parts[2]

    if 'cc1plus' in binary:
        x.append(time)
        y.append(address)
    assert len(parts) == 3

first_time = x[0]
for i in range(len(x)):
    x[i] -= first_time

fig, ax = plt.subplots()
ax.scatter(x, y, s = 0.1, c='green', alpha=0.3, edgecolors='none', marker='s')
ax.legend()
ax.grid(True)

plt.title(args.title)
plt.ylabel('Address')
plt.xlabel('Time')
plt.xlim(0, 16)
plt.ylim(0, 25 * 1024**2)
plt.savefig(args.output_image, dpi = 800)
