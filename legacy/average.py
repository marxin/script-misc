#!/usr/bin/env python3

import fileinput

c = 0
s = 0

for line in fileinput.input():
    s += float(line)
    c += 1

print(s/c)
