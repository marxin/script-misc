#!/usr/bin/env python

from __future__ import print_function

import os
import sys

if len(sys.argv) != 2:  
  exit(-1)

lines = [x.strip() for x in open(sys.argv[1]).readlines()]
print('emerge -av ' + ' '.join(lines))
