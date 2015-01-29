#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import argparse

from subprocess import *

parser = argparse.ArgumentParser(description='Get ELF build ID')
parser.add_argument('file', metavar = 'FILE', help = 'ELF file')

args = parser.parse_args()

p = Popen(['readelf', '-n', args.file], stdout = PIPE)
result, err = p.communicate()

result = result.decode('utf-8')

token = 'Build ID:'
i = result.index(token)
id = result[i + len(token):-1].strip()
print(id)
