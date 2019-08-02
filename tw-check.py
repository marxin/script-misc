#!/usr/bin/env python3

import sys
from datetime import datetime

lines = open('/etc/os-release').readlines()

version = None
for line in lines:
    if line.startswith('VERSION_ID="'):
        version = line.split('"')[1]

release_date = datetime.strptime(version, '%Y%m%d')
days = (datetime.now() - release_date).days

limit = int(sys.argv[-1])
if days < limit:
    print('OK', end = '')
else:
    print('WARNING', end = '')

print(': last Tumbleweed update before %d days (%s)' % (days, version))
exit(days >= limit)
