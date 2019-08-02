#!/usr/bin/env python3

import argparse
import os

parser = argparse.ArgumentParser(description = 'Exit with zero if size of the file is smaller')

parser.add_argument('file', help = 'Path to file')
parser.add_argument('limit', type = int, help = 'Size limit in bytes')
args = parser.parse_args()

if not os.path.exists(args.file):
    print('File not found: %s' % args.file)
    exit(2)

size = os.path.getsize(args.file)
e = not (size <= args.limit)
print('File size: %d, exit: %d' % (size, e))
exit(e)
