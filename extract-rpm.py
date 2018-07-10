#!/usr/bin/env python3

import os
import subprocess
import argparse

parser = argparse.ArgumentParser(description='Extract RPM file into a directory')
parser.add_argument('rpm', metavar = 'rpm', help = 'RPM file locaction')
parser.add_argument('folder', metavar = 'folder', help = 'Folder where to extract')
args = parser.parse_args()

if not os.path.exists(args.folder):
    os.mkdir(args.folder)

os.chdir(args.folder)
subprocess.check_output('rpm2cpio %s | cpio -idmv' % args.rpm, shell = True)
