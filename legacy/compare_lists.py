#!/usr/bin/env python3

import sys
import hashlib
import argparse
import json
import os

def print_comparison(k, s, d):
    print('%s: %d/%d %.2f' % (k, s, d, 100.0 * d / s - 100))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compare two key: value lists')
    parser.add_argument('source', metavar = 'source', help = 'Source file')
    parser.add_argument('destination', metavar = 'destination', help = 'Destination file')

    args = parser.parse_args()

    s = {}
    d = {}

    for l in open(args.source).readlines():
        x = l.strip().split(':')
        s[x[0]] = int(x[1])

    for l in open(args.destination).readlines():
        x = l.strip().split(':')
        d[x[0]] = int(x[1])

    sum_s = 0
    sum_d = 0

    for k in s:
        if k in d:
            print_comparison(k, s[k], d[k])
            sum_s += s[k]
            sum_d += d[k]

    print_comparison('TOTAL', sum_s, sum_d)
