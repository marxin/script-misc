#!/usr/bin/env python3

import fileinput

for line in fileinput.input():
    print(open(line.strip() + '.rst').read())
