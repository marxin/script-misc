#!/usr/bin/env python3

import argparse
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description='Extract RPM file into a directory')
parser.add_argument('rpm', metavar='rpm', help='RPM file locaction')
parser.add_argument('-f', '--folder', metavar='folder', default='.', help='Folder where to extract')
args = parser.parse_args()

if not os.path.exists(args.folder):
    os.mkdir(args.folder)

cmd_args = '-i' if '.src.rpm' in Path(args.rpm).name else '-idmv'
subprocess.check_output('rpm2cpio %s | cpio %s -D %s' % (args.rpm, cmd_args, args.folder), shell=True)
