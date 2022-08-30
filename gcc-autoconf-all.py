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
    configure_lines = open('configure.ac').read().splitlines()
    if any(map(lambda line: line.startswith('AC_CONFIG_HEADERS'), configure_lines)):
        subprocess.check_output(f'{ENV} autoheader-2.69 -f', shell=True, encoding='utf8')
    if any(map(lambda line: line.startswith('AM_INIT_AUTOMAKE'), configure_lines)):
        subprocess.check_output(f'{ENV} /home/marxin/bin/automake-1.15.1/bin/automake -f', shell=True, encoding='utf8')
    subprocess.check_output(f'{ENV} autoconf-2.69 -f', shell=True, encoding='utf8')
