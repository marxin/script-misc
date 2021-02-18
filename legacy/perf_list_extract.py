#!/usr/bin/env python3

import subprocess

content = subprocess.check_output('perf list hw cache', shell = True, encoding = 'utf8')

hw_events = []

for l in content.split('\n'):
    l = l.strip()
    if l != '':        
        hw_events.append(l[:l.find(' ')])

print(','.join(hw_events))
