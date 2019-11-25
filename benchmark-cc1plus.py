#!/usr/bin/env python3

import subprocess
from datetime import datetime

def run(binary):
    start = datetime.now()
    subprocess.check_output('%s /home/marxin/Programming/tramp3d/tramp3d-v4.ii -O2 -quiet' % binary, shell = True)
    return (datetime.now() - start).total_seconds()

before = '/home/marxin/Programming/gcc2/objdir/gcc/cc1plus'
after = '/dev/shm/objdir/gcc/cc1plus'

i = 0
before_total = 0
after_total = 0

while True:
    i += 1
    before_total += run(before)
    after_total += run(after)

    avg_before = before_total / i
    avg_after = after_total / i
    print('Total runs: %d, before: %.2f, after: %.2f, cmp: %.3f%%' % (i, avg_before, avg_after, 100.0 * avg_after / avg_before))
