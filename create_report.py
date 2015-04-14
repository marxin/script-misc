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
import datetime

from tempfile import *
from collections import defaultdict
from itertools import groupby
from functools import *

parser = argparse.ArgumentParser(description='Create JSON report for dashboard.')
parser.add_argument('test', help = 'test property')
parser.add_argument('compiler', help = 'compiler property')
parser.add_argument('buildbot', help = 'buildbot property')
parser.add_argument('options', help = 'compiler options property')
parser.add_argument('report', help = 'output file')
parser.add_argument('files', metavar = 'FILES', nargs = '+', help = 'JSON files with data')

def main():
    args = parser.parse_args()

    d = {
            'creation_date': str(datetime.datetime.utcnow()),
            'test': args.test,
            'compiler': args.compiler,
            'buildbot': args.buildbot,
            'options': args.options,
    }

    all_data = []
    for f in args.files:
        data = json.load(open(f))
        all_data += data

    d['data'] = all_data

    with open(args.report, 'w') as f:
        f.write(json.dumps(d, indent = 4))

if __name__ == "__main__":
    main()
