#!/usr/bin/env python3

import os
from pathlib import Path

from termcolor import colored


def get_color_by_loc(loc):
    if loc < 100:
        return 'red'
    elif loc > 1000:
        return 'cyan'
    else:
        return 'white'


totalloc = 0
alllocs = []
filelist = []
folders = {}

for root, _, files in os.walk('.'):
    for file in files:
        if file.endswith(('.rst', '.md')):
            full = Path(root, file)
            filelist.append(full)
            folders[full.parent] = 0


filelist = sorted(filelist)
filecount = len(filelist)

for file in filelist:
    loc = len(open(file).read().splitlines())
    totalloc += loc
    alllocs.append(loc)
    for f in folders.keys():
        if file.is_relative_to(f):
            folders[f] += loc

    folder = str(file.parent) + '/'
    name = file.name
    print(f'{colored(folder, "magenta")}{colored(name, "green")} [{colored(loc, get_color_by_loc(loc))}]')

print(f'\n=== TOTAL files: {filecount}')
print(f'Total LOC: {totalloc}')
print(f'Average LOC: {totalloc // filecount}')
print(f'Median LOC: {alllocs[len(alllocs) // 2]}')

print('\n=== FOLDERS ===')
for folder, count in sorted(folders.items(), key=lambda x: x[0]):
    print(f'{colored(folder, "magenta")}: {count}')
