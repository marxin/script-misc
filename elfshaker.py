#!/usr/bin/env python3

import os
import shutil
import subprocess
from pathlib import Path

hashes = open('/tmp/list.txt').read().splitlines()

for i, h in enumerate(hashes[:100]):
    print(i, '/', len(hashes), h)
    archive = f'{h}.tar'
    zstd_archive = f'{archive}.zst'
    shutil.copyfile(f'/home/marxin/DATA/gcc-binaries/{zstd_archive}', zstd_archive)
    subprocess.check_output(f'zstd -T0 -d {zstd_archive} -f', shell=True)
    subprocess.check_output(f'tar xvf {archive}', shell=True)
    os.remove(archive)
    os.remove(zstd_archive)
    print(subprocess.check_output('du -hs usr', shell=True, encoding='utf8').strip())
    assert Path('usr/local/share/man/man1/gcov-tool.1').exists()
    subprocess.check_output(f'/home/marxin/Programming/elfshaker/target/release/elfshaker store {h}', shell=True)
