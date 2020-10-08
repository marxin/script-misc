#!/usr/bin/env python3

import argparse
import subprocess

parser = argparse.ArgumentParser(description='Drive bisection of a -fdbg-cnt '
                                 'argument.')
parser.add_argument('gcc_command', help='GCC command')
parser.add_argument('run_command', help='Run command')
parser.add_argument('dbg_cnt_name', help='Debug counter name')
parser.add_argument('max_argument', type=int,
                    help='Maximum value of the debug counter')

args = parser.parse_args()

boundaries = [1, args.max_argument]

while boundaries[1] - boundaries[0] > 1:
    middle = (boundaries[1] + boundaries[0]) / 2
    print('%d:[%d, %d]' % (middle, boundaries[0], boundaries[1]))
    cmd = args.gcc_command + ' -fdbg-cnt=%s:%d' % (args.dbg_cnt_name, middle)
    subprocess.check_output(cmd, shell=True, stderr=subprocess.PIPE)
    r = subprocess.run(args.run_command, shell=True, stderr=subprocess.PIPE)
    if r.returncode == 0:
        boundaries[0] = middle
    else:
        boundaries[1] = middle

print('First bad value is -dbg-cnt=%s:%d' % boundaries[1])
