#!/usr/bin/env python3

import sys
import os
import subprocess
import json
from os.path import join, getsize

def analyze_folder(folders):
    allfiles = []

    for folder in folders:
        for root, dirs, files in os.walk(folder):
            for f in files:
                allfiles.append(join(root, f))

    elfs = []
    for i, f in enumerate(allfiles):
        try:
            r = subprocess.check_output('file "%s"' % f, shell = True, encoding = 'utf8')
            if 'ELF' in r:
                elfs.append(f)
            print('%d/%d: %s' % (i, len(allfiles), r.strip()), file = sys.stderr)
        except subprocess.CalledProcessError as e:
            print(str(e), file = sys.stderr)

    d = {}

    for i, e in enumerate(elfs):
        r = subprocess.check_output('python3 elf_info.py %s' % e, shell = True, encoding = 'utf8')
        d[e] = json.loads(r)
        print('%d/%d' % (i, len(elfs)), file = sys.stderr)

    return d

d = analyze_folder(['/lib', '/lib64', '/usr/bin', '/usr/lib', '/usr/lib64', '/usr/sbin'])
print(d)
