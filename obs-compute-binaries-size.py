#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import tempfile
import json

from termcolor import colored

parser = argparse.ArgumentParser(description = 'Get RPM sizes and sizes of ELF files')
parser.add_argument('api', help = 'API')
parser.add_argument('project', help = 'OBS project name')
parser.add_argument('repository', help = 'OBS repository')
parser.add_argument('tmp', help = 'TMP folder where to extract RPM packages')
parser.add_argument('output_folder', help = 'Output folder where to save. json files')
args = parser.parse_args()

result = subprocess.check_output('osc -A %s r %s -r %s -a %s --csv' % (args.api, args.project, args.repository, 'x86_64'), shell = True)
packages = result.decode('utf-8', 'ignore').strip().split('\n')
packages = [x.split(';')[0] for x in packages if 'succeeded' in x]
packages = [x for x in packages if x != '_' and not 'gcc' in x]

branched = set()
print('Successfull packages: %d: %s' % (len(packages), str(packages)))

binfolder = args.tmp
assert '/dev/shm' in binfolder
root = os.path.join(binfolder, 'root')

def clean():
    shutil.rmtree(binfolder, ignore_errors = True)
    os.mkdir(binfolder)

def cleanroot():
    shutil.rmtree(root, ignore_errors = True)
    os.mkdir(root)

def get_category(rpm):
    if '-devel-' in rpm:
        return 'devel'
    elif '-debuginfo-' in rpm or '-debug-' in rpm:
        return 'debug'
    else:
        return 'normal'

def process_rpm(full):
    cleanroot()
    vm = {'name': full, 'size': os.path.getsize(full), 'files': []} 

    subprocess.check_output('rpm2cpio %s | cpio -idmv -D %s' % (full, root), shell = True, stderr = subprocess.PIPE)

    r = subprocess.check_output('du -bs %s' % root, shell = True, encoding = 'utf8')
    value = int(r.strip().split('\t')[0])
    vm['extracted_size'] = value
    print('  extracting: %s: %d' % (full, value))

    # process all files
    candidates = set()
    for r, dirs, files in os.walk(root):
        for f in files:
            a = os.path.realpath(os.path.join(r, f))
            if os.path.exists(a):
                candidates.add(a)
            else:
                # TODO
                pass

    elfs = []
    for f in candidates:
        if '- ' in f:
            print('skipping due to dash %s' % f)
            continue
        try:
            r = subprocess.run('file %s' % f, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = 'utf8', timeout = 30)
            if 'ELF' in r.stdout:
                s = os.path.getsize(f)
                vm['files'].append((f, s))
                print('    file: %s: %d' % (f, s))
        except subprocess.TimeoutExpired:
            print('timeout %s' % f)
            pass

    return vm

def process_category(name):
    vm = []
    for f in os.listdir(binfolder):
        full = os.path.join(binfolder, f)
        if f.endswith('.rpm') and get_category(f) == name:
            vm.append(process_rpm(full))

    return vm

for i, p in enumerate(packages):
    if p in branched:
        print('Skipping, branched: %s' % p)
        continue

    print('Downloading: %s (%d/%d)' % (p, i, len(packages)))
    jsonfile = os.path.join(args.output_folder, p + '.json')
    if os.path.exists(jsonfile):
        continue

    clean()
    try:
        vm = {'name': p, 'sections': {}}
        subprocess.check_output('osc -A %s getbinaries %s %s %s x86_64 --debug -d %s' % (args.api, args.project, p, args.repository, binfolder), shell = True, stderr = subprocess.PIPE)
        vm['sections']['normal'] = process_category('normal')
        vm['sections']['devel'] = process_category('devel')
        vm['sections']['debug'] = process_category('debug')
        with open(jsonfile, 'w') as of:
            json.dump(vm, of)
        
    except subprocess.CalledProcessError as e:
        print(str(e))
