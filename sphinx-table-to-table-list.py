#!/usr/bin/env python3

import sys


def split_by_columns(line, widths):
    parts = []
    while line:
        w = widths[0]
        # lst
        if len(widths) == 1:
            w = 1000
        parts.append(line[:w].rstrip())
        line = line[w + 1:]
        widths = widths[1:]
    return parts


lines = sys.stdin.read().strip().splitlines()

header = lines[0]
assert '= =' in header
widths = [len(x) for x in header.split(' ')]

# skip header
lines = lines[1:]
# skip footer
if '= =' in lines[-1]:
    lines = lines[:-1]

output = []
for line in lines:
    columns = split_by_columns(line, widths)
    nonempty = len([col for col in columns if col])
    if len(widths) == nonempty:
        output.append(columns)
    else:
        for i, column in enumerate(columns):
            if column:
                output[-1][i] += ' ' + column

print('.. list-table::')
has_header = False
if output[1][0] == '=' * widths[0]:
    print('   :header-rows: 1')
    output = output[:1] + output[2:]
    has_header = True
print()

for i, columns in enumerate(output):
    for j, value in enumerate(columns):
        c = '*' if j == 0 else ' '
        print(f'   {c} - {value}')
    if i == 0 and has_header:
        print()
