#!/usr/bin/env python

import os
import sys
import re

from itertools import groupby

if len(sys.argv) <= 1:
  print('usage: ipa_se_grep [file]')
  exit(-1)

lines = map(lambda x: x.strip(), open(sys.argv[1]).readlines())

pattern = '^(Callgraph.*)|(Varpool)'

matches = filter(lambda x: re.match(pattern, x), lines)

groups = [(key, list(group)) for key, group in groupby(sorted(matches))]

for i in sorted(groups, key = lambda x: len(x[1]), reverse = True):
	print('%-45s:%u' % (i[0], len(i[1])))
