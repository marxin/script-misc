#!/usr/bin/env python3

import re
import requests
import sys

REGEX = re.compile('.*A HREF.*\[gcc r11-([0-9]*).*')

lines = requests.get('https://gcc.gnu.org/pipermail/gcc-cvs/2020-November/date.html').text.split('\n')
revisions = []

for line in lines:
    m = REGEX.match(line)
    if m:
        revisions.append(int(m.group(1)))

if not revisions:
    sys.exit(0)

start = min(revisions)
end = max(revisions)
has_failure = False

while start != end:
    if start not in revisions and start > int(sys.argv[1]):
        print(f'Missing: {start}')
        has_failure = True
    start += 1

print(f'Range: {min(revisions)}-{end}')
sys.exit(1 if has_failure else 0)
