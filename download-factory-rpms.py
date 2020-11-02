#!/usr/bin/env python3

import glob
import os
from pathlib import Path
import shutil
import subprocess
import sys
import concurrent.futures

PWD = '/home/marxin/BIG/rpm/'

shutil.rmtree(PWD, ignore_errors=True)
os.mkdir(PWD)

# projects = ['openSUSE:Factory:Rings:0-Bootstrap', 'openSUSE:Factory:Rings:1-MinimalX']
projects = ['openSUSE:Factory']

packages = []
for project in projects:
    packages += subprocess.check_output(f'osc ls {project}', shell=True, encoding='utf8').splitlines()

packages = sorted(packages)
packages = ['rpmlint-mini-AGGR'] + packages

def get_package(package):
    print(package)
    os.chdir(PWD)
    os.mkdir(package)
    os.chdir(package)
    subprocess.check_output(f'osc getbinaries --source openSUSE:Factory {package} standard x86_64', shell=True, stderr=subprocess.DEVNULL)
    source_rpms = glob.glob('binaries/*.src.rpm')
    if len(source_rpms) == 1:
        subprocess.check_output(f'extract-rpm.py {source_rpms[0]} SRC', shell=True, stderr=subprocess.DEVNULL)
        # for now do not check src.rpm files
        os.remove(source_rpms[0])
        rpmlintrc_files = glob.glob('SRC/*rpmlintrc')
        for rpmlintrc in rpmlintrc_files:
            shutil.copy(rpmlintrc, '.')
        shutil.rmtree('SRC', ignore_errors=True)


with concurrent.futures.ProcessPoolExecutor(max_workers=64) as executor:
    futures = []
    for package in packages:
        futures.append(executor.submit(get_package, package))
    concurrent.futures.wait(futures)
