#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path

AUTOCONF_BIN = '/home/worker/bin/autoconf'
AUTOMAKE_BIN = '/home/worker/bin/automake'
ACLOCAL_BIN = '/home/worker/bin/aclocal'
AUTOHEADER_BIN = '/home/worker/bin/autoheader'

ENV = f'AUTOCONF={AUTOCONF_BIN} ACLOCAL={ACLOCAL_BIN} AUTOMAKE={AUTOMAKE_BIN}'

config_folders = []

for root, _, files in os.walk('.'):
    for file in files:
        if file == 'configure':
            config_folders.append(Path(root).resolve())

for folder in sorted(config_folders):
    print(folder, flush=True)
    os.chdir(folder)
    configure_lines = open('configure.ac').read().splitlines()
    if any(_ for line in configure_lines if line.startswith('AC_CONFIG_HEADERS')):
        subprocess.check_output(f'{ENV} {AUTOHEADER_BIN} -f', shell=True, encoding='utf8')
    # apparently automake is somehow unstable -> skip it for gotools
    if (any(_ for line in configure_lines if line.startswith('AM_INIT_AUTOMAKE'))
            and not str(folder).endswith('gotools')):
        subprocess.check_output(f'{ENV} {AUTOMAKE_BIN} -f',
                                shell=True, encoding='utf8')
    subprocess.check_output(f'{ENV} {AUTOCONF_BIN} -f', shell=True, encoding='utf8')
