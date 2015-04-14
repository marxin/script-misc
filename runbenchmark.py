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

from tempfile import *
from collections import defaultdict
from itertools import groupby
from functools import *

parser = argparse.ArgumentParser(description='Run benchmark and create JSON report.')
parser.add_argument('executable', help = 'executed binary')
parser.add_argument('report', help = 'file where results are saved')
parser.add_argument('--args', dest = 'args', help = 'benchmark arguments')
parser.add_argument('--iterations', dest = 'iterations', type = int, help = 'number of iterations of the benchmark', default = 3)
parser.add_argument('--parser', dest = 'parser',  help = 'result parser', choices = ['tramp3d'])

def geomean(values):
    return reduce(lambda x, y: x * y, values, 1) ** (1.0 / len(values))

def avg(values):
    return sum(values) / len(values)

class Tramp3dParser:
    def parse(self, lines):
        s = 'Time spent in iteration:'
        f = list(filter(lambda x: x.startswith(s), lines))
        values = list(map(lambda x: float(x[len(s):]), f))
        print(values)
        return geomean(values)

def main():
    args = parser.parse_args()

    all_lines = []

    for i in range(args.iterations):
        cmd = '%s %s' % (args.executable, args.args)
        ps = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
        
        lines = [x.decode('utf-8').rstrip() for x in ps.stdout.readlines()]
        all_lines += lines

    value = None
    if args.parser == 'tramp3d':
        value = Tramp3dParser().parse(all_lines)

    with open(args.report, 'w') as f:
        f.write(json.dumps([{ 'name': 'iteration time', 'type': 'time', 'values': { 'geomean': value }}], indent=4))

if __name__ == "__main__":
    main()
