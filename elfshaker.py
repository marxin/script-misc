#!/usr/bin/env python3

import os
import shutil
import subprocess
import time
from pathlib import Path

from git import Repo


def wipe_loose():
    shutil.rmtree('elfshaker_data/loose', ignore_errors=True)
    shutil.rmtree('elfshaker_data/packs/loose', ignore_errors=True)


CHUNK_SIZE = 100
last_revision = '58a41b43b5f02c67544569c508424efa4115ad9f'
repo = Repo('/home/marxin/Programming/gcc2')
elfshaker_repo = '/home/marxin/elfshaker-gcc-binaries'

revisions = [x.hexsha for x in reversed(list(repo.iter_commits(last_revision + '..origin/master', first_parent=True)))]
revcount = len(revisions)
print(f'Have: {revcount} revisions')

shutil.rmtree(elfshaker_repo, ignore_errors=True)
os.mkdir(elfshaker_repo)
os.chdir(elfshaker_repo)

for i in range(revcount // CHUNK_SIZE):
    wipe_loose()
    print(f'{i + 1}/{revcount // CHUNK_SIZE}')
    if os.path.exists('elfshaker_data'):
        mbsize = int(subprocess.check_output('du -s elfshaker_data', shell=True, encoding='utf8').split()[0])
        mbsize /= 1024
        print(f'Size {mbsize / (i * CHUNK_SIZE):.2f} MiB per revision')
    chunk = revisions[:CHUNK_SIZE]
    print('  ' + '.' * CHUNK_SIZE)
    print('  ', end='')

    start = time.monotonic()
    for h in chunk:
        archive = f'{h}.tar'
        zstd_archive = f'{archive}.zst'
        abs_zstd_archive = f'/home/marxin/DATA/gcc-binaries/{zstd_archive}'
        if Path(abs_zstd_archive).exists():
            print('#', end='', flush=True)
            shutil.copyfile(abs_zstd_archive, zstd_archive)
            subprocess.check_output(f'zstd -T0 -d {zstd_archive} -f', shell=True, stderr=subprocess.DEVNULL)
            subprocess.check_output(f'tar xvf {archive}', shell=True)
            os.remove(archive)
            os.remove(zstd_archive)
            subprocess.check_output(f'/home/marxin/Programming/elfshaker/target/release/elfshaker store {h}',
                                    shell=True)
        else:
            print('.', end='', flush=True)
    print()
    duration = time.monotonic() - start
    print(f'Store took {duration / CHUNK_SIZE:.2f}s per revision')

    start = time.monotonic()
    subprocess.check_output(f'~/Programming/elfshaker/target/release/elfshaker pack pack-{i} --compression-level 19',
                            shell=True, stderr=subprocess.PIPE)
    revisions = revisions[CHUNK_SIZE:]
    duration = time.monotonic() - start
    print(f'Pack took {duration / CHUNK_SIZE:.2f}s per revision')
