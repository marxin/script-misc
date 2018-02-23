#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os

parser = argparse.ArgumentParser(description = 'Analyze OBS log files')
parser.add_argument('location', help = 'Folder with logs')
parser.add_argument('--verbose', help = 'Verbose', action='store_true')
args = parser.parse_args()

def is_interesting(line):
    if 'Segmentation fault' in line or 'internal compiler error' in line:
        return True

    if 'error:' in line and not 'Bad exit status from' in line:
        return True
    
    return False

for root, dirs, files in os.walk(args.location):
    for f in files:
        lines = [x.strip() for x in open(os.path.join(root, f)).readlines()]
        interesting = [l for l in lines if is_interesting(l)]

        print('%s: %d' % (f, len(interesting)))
        if (args.verbose):
            for i in interesting:
                print('    ' + i)
