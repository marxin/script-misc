#!/usr/bin/env python3

import fileinput
import json
import sys
import os
import subprocess
import shutil

def find_binary(folder, name):
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f == name:
                return os.path.join(root, f)

    return None

def get_binary_info(path):
    r = subprocess.check_output('~/Programming/buildbot-scripts/elf_info.py ' + path, shell = True)
    data = json.loads(r)
    r = []
    for d in data:
        k = 'size' if 'size' in d else 'count'
        v = d[k]
        if k == 'size':
            v = 1.0 * v / (1024 * 1024)
            r.append((d['name'] + ' (MB)', '%.2f' % (v)))
        else:
            r.append((d['name'], v))

    return r

if len(sys.argv) != 2:
    print('Usage: <folder>')
    exit(1)

def process_binary(executable):
    print('=== %s ===' % executable)
    results = []
    for f in os.listdir(sys.argv[1]):
        full = os.path.join(sys.argv[1], f)
        if os.path.isdir(full):
            print(f)
            binary = find_binary(full, executable)
            r = get_binary_info(binary)
            name = '/dev/shm/tmp.out'
            shutil.copyfile(binary, name)
            subprocess.check_output('strip ' + name, shell = True)
            r2 = get_binary_info(name)
            results.append((f, r, r2))

    results = sorted(results, key = lambda x: x[0], reverse = True)

    print(';', end = '')
    for key in results[0][1]:
        print(key[0] + ';' , end = '')
    print()

    for r in results:
        print(r[0] + ';', end = '')
        for i, key in enumerate(results[0][1]):
            print(str(r[1][i][1]) + ';', end = '')

        print()

    print('Stripped')
    for r in results:
        print(r[0] + ';', end = '')
        for i, key in enumerate(results[0][2]):
            print(str(r[2][i][1]) + ';', end = '')

        print()

process_binary('cc1')
process_binary('cc1plus')
