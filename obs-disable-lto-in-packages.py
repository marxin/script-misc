#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import tempfile
import fileinput

from termcolor import colored

parser = argparse.ArgumentParser(description = 'Disable LTO in a package')
parser.add_argument('package')
parser.add_argument('bugid')
args = parser.parse_args()

r = subprocess.check_output('osc branch openSUSE:Factory %s' % (args.package), shell = True, encoding = 'utf8')

command = None

for line in r.split('\n'):
    line = line.strip()
    if line.startswith('osc co'):
        command = line
        break

assert command != None

tmp = tempfile.mkdtemp()
print(tmp)
os.chdir(tmp)

subprocess.check_output(command, shell = True)
l = command.split(' ')[-1]
print(l)
os.chdir(l)

spec = '%s.spec' % args.package
newspec = '%s.spec.new' % args.package

lines = list(open(spec).readlines())

with open(newspec, 'w+') as w:
    for l in lines:
        w.write(l)
        if l.startswith('%build'):
            w.write('%define _lto_cflags %{nil}\n')

shutil.copyfile(newspec, spec)
subprocess.check_output('osc vc -m "Disable LTO (boo#%s)."' % (args.bugid), shell = True)
subprocess.check_output('osc commit -m "Disable LTO (boo#%s)."' % args.bugid, shell = True)
subprocess.check_output('osc sr -m "Disable LTO (boo#%s)."' % args.bugid, shell = True)

shutil.rmtree(tmp)
