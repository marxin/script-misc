#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import re
import argparse
import tempfile
import shutil
import time
import subprocess
import json

parser = argparse.ArgumentParser(description='Parse botan results')
parser.add_argument('input', help = 'Input file')
parser.add_argument('output', help = 'JSON report file')

def get_tokens(line):
    return list(filter(None, line.split(' ')))

def get_bitmap_section(lines):
    start = False
    filtered = []

    for l in lines:
        if l.startswith('Bitmap'):
            start = True

        if start:
            filtered.append(l)

        if start and l.startswith('Total'):
            return filtered[2:]

    return None

def get_vector_section(lines):
    start = False
    filtered = []

    for l in lines:
        if l.startswith('Heap vectors'):
            start = True

        if start:
            filtered.append(l)

        if start and l.startswith('Total'):
            return filtered[2:]

    return None

def main():
    args = parser.parse_args()

    lines = [x.strip() for x in open(args.input).readlines()]

    bitmap = get_bitmap_section(lines)
    bitmap_total_leak = sum([int(get_tokens(x)[5]) for x in bitmap[:-2]])

    vectors = get_vector_section(lines)
    vectors_total_leak = int(get_tokens(vectors[-1])[1])

    total_memory = int(get_tokens([x for x in lines if x.startswith('Total Allocated:')][0])[2])

    d = {'bitmap_leak': bitmap_total_leak, 'vector_leak': vectors_total_leak, 'total_memory': total_memory}

    with open(args.output, 'w') as o:
        o.write(json.dumps([{'name': 'gcc_memory_profile', 'type': 'memory profile', 'values': d}], indent = 4))

if __name__ == "__main__":
    main()
