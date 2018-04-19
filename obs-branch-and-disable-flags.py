#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import tempfile

from termcolor import colored

parser = argparse.ArgumentParser(description = 'OBS hacking')
parser.add_argument('project', help = 'OBS project name')
parser.add_argument('repository', help = 'OBS repository')
args = parser.parse_args()

result = subprocess.check_output('osc r %s -r %s -a %s --csv' % (args.project, args.repository, 'x86_64'), shell = True)
packages = result.decode('utf-8', 'ignore').strip().split('\n')
packages = [x.split(';')[0] for x in packages if 'failed' in x]
packages = [x for x in packages if x != '_' and not 'gcc' in x]

print('Failed packages: %d: %s' % (len(packages), str(packages)))

for p in packages:
    print('Branching: %s' % p)
    try:
        subprocess.check_output('osc branch openSUSE:Factory %s %s' % (p, args.project), shell = True)
    except subprocess.CalledProcessError as e:
        print(str(e))

tmp = tempfile.mkdtemp()
print(tmp)
os.chdir(tmp)

for p in packages:
    os.chdir(tmp)
    print('osc co: %s' % p)    
    subprocess.check_output('osc co %s/%s' % (args.project, p), shell = True)
    os.chdir(os.path.join(args.project, p))
    spec = p + '.spec'
    assert os.path.exists(spec)

    data = None
    with open(spec, 'r') as original:
        data = original.read()

    with open(spec, 'w') as modified:
        modified.write("%global optflags -fmessage-length=0 -grecord-gcc-switches -O2 -Wall -D_FORTIFY_SOURCE=2 -fstack-protector-strong -funwind-tables -fasynchronous-unwind-tables -fstack-clash-protection -g\n" + data)

    subprocess.check_output('osc commit -m "Disable LTO" --noservice', shell = True)
