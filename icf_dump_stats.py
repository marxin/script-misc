#!/usr/bin/env python3

import sys
from itertools import *

if len(sys.argv) != 2:
    exit(1)

candidates = []
buffer = []
d = {}
state = True

def is_candidate(lines):    
    return len(lines) > 0 and lines[-1].startswith('Equals called') and lines[-1].endswith('false')

def trim_for_code(lines):
    return list(filter(lambda x: x[0] == ' ', lines))

keyfunc = lambda x: '#'.join(x)

with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip('\n')
        if line == '':
            if is_candidate(buffer):
                t = trim_for_code(buffer)
                candidates.append(t)
                d[keyfunc(t)] = '\n'.join(buffer)
            buffer = []
            state = False
        else:
            state = True
            buffer.append(line)

if is_candidate(buffer):
    candidates.append(trim_for_code(buffer))


grouped_list = []

data = sorted(candidates, key = keyfunc)
for k, g in groupby(data, keyfunc):
    grouped_list.append((len(list(g)), k))

for i in list(sorted(grouped_list, key = lambda x: x[0], reverse = True))[0:20]:
    print('Times: %u' % i[0])
    print('Stack: ' + d[i[1]] + '\n')

