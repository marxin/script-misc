#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path

ENV = 'AUTOCONF=autoconf-2.69 ACLOCAL=~/bin/automake-1.15.1/bin/aclocal  AUTOMAKE=~/bin/automake-1.15.1/bin/automake'

config_folders = []

for root, _, files in os.walk('.'):
    for file in files:
        if file == 'configure':
            config_folders.append(Path(root).resolve())

for folder in config_folders:
    print(folder)
    os.chdir(folder)
    if 'AC_CONFIG_HEADERS' in open('configure.ac').read():
        subprocess.check_output(f'{ENV} autoheader-2.69 -f', shell=True, encoding='utf8')
    subprocess.check_output(f'{ENV} autoconf-2.69 -f', shell=True, encoding='utf8')
