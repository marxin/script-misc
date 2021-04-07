#!/usr/bin/env python3

import os
import shutil
import subprocess

INPUT = '/tmp/gcc-xml'
OUTPUT = '/tmp/gcc-rst'

shutil.rmtree(OUTPUT, ignore_errors=True)
os.mkdir(OUTPUT)
shutil.copy('templates/baseconf.py', OUTPUT)

for xml in os.listdir(INPUT):
    base, _ = os.path.splitext(xml)
    shutil.rmtree('output', ignore_errors=True)
    r = subprocess.check_output(f'/home/marxin/Programming/texi2rst/texi2rst.py {INPUT}/{xml}', shell=True,
                                encoding='utf8')
    shutil.move('output', os.path.join(OUTPUT, base))
    config = f'templates/{base}/conf.py'
    if os.path.exists(config):
        shutil.copy(config, os.path.join(OUTPUT, base))
    shutil.copy('templates/Makefile', os.path.join(OUTPUT, base))
    with open(os.path.join(OUTPUT, base, 'index.rst'), 'w') as w:
        w.write(open('templates/index.rst').read().replace('__doc__', base))
