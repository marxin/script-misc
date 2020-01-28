#!/usr/bin/env python3

import subprocess
import os
from datetime import datetime

files = sorted([x for x in os.listdir('.') if x.endswith('.ii')])
print(files)

def make_run(compiler, f, level):
    cmd = '%s -O2 -flto -c -ftime-report -o/dev/shm/x.o %s' % (compiler, f)
    if level != None:
        cmd += ' -flto-compression-level=%d' % level
#    print(cmd)
    start = datetime.now()
    r = subprocess.run (cmd, shell = True, encoding = 'utf8', stderr = subprocess.PIPE)
    duration = (datetime.now() - start).total_seconds()
    assert r.returncode == 0
    compression = None
    lines = r.stderr.split('\n')
    for l in lines:
        if 'lto stream compression' in l:
            parts = [x for x in l.split(')') if x]
            compression = float(parts[2].strip().split(' ')[0])

    size = os.stat('/dev/shm/x.o').st_size

    cmd = 'gcc -O2 -flto -ftime-report /dev/shm/x.o'
    start2 = datetime.now()
    r = subprocess.run (cmd, shell = True, encoding = 'utf8', stderr = subprocess.PIPE)
    duration2 = (datetime.now() - start2).total_seconds()
    decompression = 0
    lines = r.stderr.split('\n')
    for l in lines:
        if 'lto stream decompression' in l:
            parts = [x for x in l.split(')') if x]
            decompression = float(parts[2].strip().split(' ')[0])
#            print(l)
    return (size, compression, duration, decompression, duration2)

for f in files:
    print('zlib:%s:default:' % f, end = '')
    result = make_run('~/bin/gcc2/bin/gcc', f, None)
    print('%.2f:%.2f:%.2f:%.2f:%.2f' % (1.0 * result[0] / (2**20), result[1], result[2], result[3], result[4]))

for f in files:
    for l in range(3, 12):
        print('zstd:%s:%d:' % (f, l), end = '')
        result = make_run('gcc', f, l)
        print('%.2f:%.2f:%.2f:%.2f:%.2f' % (1.0 * result[0] / (2**20), result[1], result[2], result[3], result[4]))
