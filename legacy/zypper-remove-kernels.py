#!/usr/bin/env python3

import subprocess
from semantic_version import Version

r = subprocess.check_output("zypper se -s 'kernel-default*'", shell = True,
        encoding = 'utf8')

remove = []

for line in r.split('\n'):
    tokens = [x.strip() for x in line.split('|')]
    if len(tokens) != 6:
        continue

    if tokens[1] == 'kernel-default':
        remove.append(tokens[3])

remove = sorted(remove, key = lambda x: Version(x))
last = remove[-1]
remove = [x for x in remove if x != last]

print('zypper rm ', end = '')
for r in remove:
    print('kernel-default-' + r + ' ', end = '')
print()
