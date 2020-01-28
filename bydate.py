#!/usr/bin/env python3

import datetime
import subprocess

a = 8 * [0]
N = 100000

r = subprocess.check_output('git log HEAD~%d..HEAD --date=short --pretty=format:%%ad' % N, shell = True, encoding = 'utf8')

for l in r.split('\n'):
    dw = datetime.datetime.strptime(l, '%Y-%m-%d').isoweekday()
    a[dw] += 1

print(a)
