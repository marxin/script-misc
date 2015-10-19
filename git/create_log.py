#!/usr/bin/env python

import os
import sys

files = sys.argv[1:]

for f in files:
    lines = open(f).readlines()
    modified = []
    subject = None
    for l in lines:
        if l.startswith('diff'):
            t = l.strip().split(' ')[-1].split('/')[-1]
            if t != 'hsa.h':
                modified.append(t)
        elif l.startswith('Subject'):
            subject = l.split(' ')[-1].strip().rstrip('.')

    with open(f + '.v2', 'w+') as wf:
        for l in lines[0:4]:
            wf.write(l)

        wf.write('\ngcc/ChangeLog:\n\n')
        wf.write('2015-10-19  Martin Liska  <mliska@suse.cz>\n\n')
        wf.write('\t* hsa.h (%s): Prefix all member variables.\n' % subject)
        for m in modified:
            wf.write('\t* ' + m + ': Likewise.\n')

        for l in lines[4:]:
            wf.write(l)
