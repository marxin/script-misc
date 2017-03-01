#!/usr/bin/env python3

import argparse
import subprocess
import random
import sys
import glob

assert len(sys.argv) >= 2

pattern = 'internal compiler error'
if len(sys.argv) == 3:
    pattern = sys.argv[2]

def does_ice(command):
    r = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stderr = r.stderr.decode('utf-8')
    return r.returncode == 124 or pattern in stderr

def do_cmd(base, flags):
    return 'timeout 3 %s %s' % (' '.join(base), ' '.join(flags))

command_line = [x.replace('#', '--param ') for x in sys.argv[1].replace('--param ', '#').split(' ') if x != '']

base = [x for x in command_line if not x.startswith('-')]
flags = set([x for x in command_line if not x in base])

def reduce(base, flags):
    while True:
        change = False
        for f in list(flags):
            flags.remove(f)
            if does_ice(do_cmd(base, flags)):
                change = True
                break
            else:
                flags.add(f)

        if not change:
            return do_cmd(base, flags)

print(reduce(base, flags))
