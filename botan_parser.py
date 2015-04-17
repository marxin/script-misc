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

def main():
    args = parser.parse_args()

    lines = [x.strip() for x in open(args.input).readlines()]

    throughput_tests = [x for x in lines if x.endswith('byte blocks')]
    basic_tests = [x for x in lines if not x in throughput_tests]

    d = {}

    for i in throughput_tests:
        i = i.rstrip(' byte blocks')
        tokens = i.split(' ')
        chunk_size = tokens[-1]
        benchmark = '%s[%s]' % (tokens[0], chunk_size)
        d[benchmark] = float(tokens[1])

    for i in basic_tests:
        index = i.find(' ')
        tokens = i[index + 1:].split(' ')

        for j in range(0, len(tokens), 2):
            d['%s%s' % (i[:index], tokens[j])] = float(tokens[j + 1])

    print(json.dumps({'name': 'throughput', 'type': 'benchmark result', 'values': d}, indent = 4))

if __name__ == "__main__":
    main()
