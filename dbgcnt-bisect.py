#!/usr/bin/env python3

import argparse
import math
import subprocess

parser = argparse.ArgumentParser(description='Drive bisection of a -fdbg-cnt '
                                 'argument.')
parser.add_argument('gcc_command', help='GCC command')
parser.add_argument('run_command', help='Run command')
parser.add_argument('dbg_cnt_name', help='Debug counter name')
parser.add_argument('max_argument', type=int,
                    help='Maximum value of the debug counter')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Verbose output')

args = parser.parse_args()


def format_dbgcnt(needed, start, end):
    s = ':'.join(['%d-%d' % (x, x) for x in needed])
    if s:
        s += ':'
    return ' -fdbg-cnt=%s:%s%d-%d' % (args.dbg_cnt_name, s, start, end)


def test(minimum, maximum, needed, count):
    steps = math.ceil(math.log2(count))
    extra_arg = format_dbgcnt(needed, minimum, maximum)
    print('%s (steps ~ %d)' % (extra_arg.lstrip(), steps))
    cmd = args.gcc_command + extra_arg
    subprocess.check_output(cmd, shell=True, stderr=subprocess.PIPE)
    r = subprocess.run(args.run_command, shell=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       encoding='utf8')
    if args.verbose:
        print(r.stdout)
        print(r.stderr)
    return r.returncode == 0


def avg(boundaries):
    return int((boundaries[0] + boundaries[1]) / 2)


def shrinken(start, end, needed):
    print('Needed: %s' % str(needed))
    boundaries = [start, end]

    while boundaries[1] - boundaries[0] > 1:
        middle = avg(boundaries)
        r = test(1, middle, needed, boundaries[1] - boundaries[0])
        if r:
            boundaries[0] = middle
        else:
            boundaries[1] = middle

    maximum = boundaries[1]

    boundaries = [start, maximum]
    while boundaries[1] - boundaries[0] > 1:
        middle = avg(boundaries)
        r = test(middle, maximum, needed, boundaries[1] - boundaries[0])
        if r:
            boundaries[1] = middle
        else:
            boundaries[0] = middle

    minimum = boundaries[0]
    return (minimum, maximum)


needed = []
boundaries = [1, args.max_argument]

while True:
    next_boundaries = shrinken(boundaries[0], boundaries[1], needed)
    needed.append(next_boundaries[0])
    needed.append(next_boundaries[1])
    if next_boundaries[1] - next_boundaries[0] <= 1:
        break

print(format_dbgcnt(needed, 0, 0))
