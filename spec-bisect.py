#!/usr/bin/env python3

import argparse
import sys

DESCR = 'Bisect SPEC benchmark run-time (parses .rsf tfile)'
parser = argparse.ArgumentParser(description=DESCR)

parser.add_argument('limit', type=float, help='Time limit in seconds')
parser.add_argument('-s', '--silent', action='store_true',
                    help='Do not print runspec/cpuspec output')
args = parser.parse_args()

rst = None

for line in sys.stdin:
    if 'format: raw' in line:
        assert not rst
        rst = line.split()[-1]
    if not args.silent:
        print(line, end='')

print(f'Parsing {rst}')

lines = open(rst).read().splitlines()
reported = [line for line in lines if '.reported_time' in line]
assert len(reported) == 1

reported_time = float(reported[0].split()[-1])
fraction = 100.0 * reported_time / args.limit
print(f'SPEC run-time: {reported_time:.2f}s, limit: {args.limit:.2f}s '
      f'({fraction:.2f}%)')
exit_code = 0 if reported_time <= args.limit else 1
print(f'Exit code: {exit_code}')
sys.exit(exit_code)
