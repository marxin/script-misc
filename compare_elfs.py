#!/usr/bin/env python3

import sys
import hashlib
import argparse
import json
import os

from readelf_sections import *

parser = argparse.ArgumentParser(description='Compare ELF binaries or folders with a bunch of binaries.')
parser.add_argument('source', metavar = 'source', help = 'Source ELF file or folder')
parser.add_argument('target', metavar = 'target', help = 'Target ELF file or folder')

args = parser.parse_args()

if os.path.isdir(args.source) and os.path.isdir(args.target):
    source_files = os.listdir(args.source)
    target_files = os.listdir(args.target)
    files = set(source_files + target_files)

    for f in files:
        if not f in source_files:
            print('Missing is source: %s' % f)
        elif not f in target_files:
            print('Missing is target: %s' % f)
        else:
            e1 = ElfInfo(os.path.join(args.source, f))
            e2 = ElfInfo(os.path.join(args.target, f))
            e1.compare(e2)
