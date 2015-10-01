#!/usr/bin/env python

import sys
import os
import subprocess

if len(sys.argv) != 3:
    print('./replace_brig.py ELF BRIG')

elf_filename = sys.argv[1]
brig_filename = sys.argv[2]

lines = subprocess.check_output(['readelf', '-S', elf_filename])

offset = -1
size = -1
lines = lines.split('\n')
for i, l in enumerate(lines):
    if '.brig' in l:
        offset = int(l.split(' ')[-1], 16)
        size = int(lines[i + 1].strip().split(' ')[0], 16)

if offset == -1:
    exit(1)

file_size = os.stat(brig_filename).st_size

if file_size > size:
    print('FATAL error: BRIG image file is bigger than corresponding section in ELF file (%u/%u)' % (file_size, size))
    exit(2)

cmd = ('dd if=%s seek=%u ibs=1 obs=1 of=%s conv=notrunc' % (brig_filename, offset, elf_filename)).split(' ')
print(cmd)
subprocess.check_output(cmd)
