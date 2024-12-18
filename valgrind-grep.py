#!/usr/bin/env python3

import argparse


def canonize_back_trace(bt):
    return tuple(line[line.find(':') + 1:].strip() for line in bt)


def skip_bt(bt, exclude):
    for line in bt:
        if '/usr/bin/as' in line or 'collect2.c' in line:
            return True
        for ex in exclude:
            if ex in line:
                return True
    return False


bt_dict = {}

parser = argparse.ArgumentParser(description='Group valgrind memory leaks')
parser.add_argument('file', help='File with valgrind errors')
parser.add_argument('--exclude', '-e',
                    help='Exclude needles (separated by comma)')
args = parser.parse_args()

if args.exclude:
    args.exclude = args.exclude.split(',')
else:
    args.exclude = []

lines = [line.strip() for line in open(args.file).readlines()]
for i in range(len(lines)):
    line = lines[i]
    if 'are definitely lost' in line:
        i += 1
        bt = []
        while not lines[i].endswith('=='):
            bt.append(lines[i])
            i += 1
        bt = canonize_back_trace(bt)
        if not skip_bt(bt, args.exclude):
            bt_dict.setdefault(bt, 0)
            bt_dict[bt] += 1

for bt, count in sorted(bt_dict.items(), key=lambda x: x[1], reverse=True):
    print(f'=== {count}x ===')
    print('\n'.join(bt))
    print()
