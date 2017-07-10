#!/usr/bin/env python3

import argparse
import subprocess
import random
import sys
import glob

assert len(sys.argv) >= 2

pattern = 'nternal compiler error'

if len(sys.argv) == 3:
    pattern = sys.argv[2]

def does_ice(command):
    r = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stderr = r.stderr.decode('utf-8')
    return r.returncode == 124 or pattern in stderr or ('in ' in stderr and ' at ' in stderr) or 'Segmentation fault' in stderr

def do_cmd(base, flags):
    return 'timeout 10 %s %s' % (' '.join(base), ' '.join(flags))

def strip_timeout(command):
    tokens = command.split(' ')
    while len(tokens) > 0 and tokens[0] == 'timeout':
        tokens = tokens[2:]

    return ' '.join(tokens)

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
            cmd = do_cmd(base, flags)
            stripped = strip_timeout(cmd)
            return stripped if does_ice(stripped) else cmd

print(reduce(base, flags))
