#!/usr/bin/env python3

import os
import sys
import re

if len(sys.argv) <= 1:
    print('usage: cpp-default-ctor [file]')
    exit(-1)

mapping = {}
mapping['tree'] = 'NULL_TREE'
mapping['unsigned'] = '0'
mapping['int'] = '0'
mapping['bool'] = 'false'
mapping['gimple'] = 'NULL'

lines = map(lambda x: x.strip(), filter(lambda x: x.strip().endswith(';'), open(sys.argv[1]).readlines()))

ctor = ''

for line in lines:
    tokens = line.rstrip(';').split(' ')
    f = tokens[0]

    ctor += tokens[-1].strip('*') + ' ('
    if f in mapping:
        ctor += mapping[f]
    elif f == 'enum':
        ctor += '(' + ' '.join(tokens[:-1]) + ') 0'
    else:
        ctor += '0'

    ctor += '), '

print(ctor)
