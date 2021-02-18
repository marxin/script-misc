#!/usr/bin/env python

import fileinput

for line in fileinput.input():
    i = line.find('execv')
    line = line[i:]
    s = line.find('[') + 1
    e = line.find(']')
    cmd = line[s:e]
    cmd = cmd.replace('"', '').replace(',', '')
    print(cmd)
