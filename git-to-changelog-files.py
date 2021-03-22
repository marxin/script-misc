#!/usr/bin/env python3

import datetime
import os
import subprocess
from itertools import dropwhile, takewhile


def is_not_changelog(line):
    return not line.endswith('ChangeLog:')


cwd = os.getcwd()

lines = subprocess.check_output('git show -s --format=%B', shell=True, encoding='utf8').splitlines()

lines = list(dropwhile(is_not_changelog, lines))

while lines:
    changelog = lines[0].rstrip(':')
    chunk = list(takewhile(is_not_changelog, lines[1:]))
    lines = lines[len(chunk) + 1:]
    data = open(changelog).read()
    with open(changelog, 'w') as f:
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        f.write(f'{date}  Martin Liska  <mliska@suse.cz>')
        f.write('\n' + '\n'.join(chunk) + '\n')
        f.write(data)
