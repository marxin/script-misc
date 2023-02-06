#!/usr/bin/env python3

import concurrent.futures
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path

from git import Repo


CHUNK_SIZE = 100
COMPRESSION_LEVEL = 17
last_revision = '1a46d358050cf6964df0d8ceaffafd0cc88539b2'
repo = Repo('/home/marxin/Programming/gcc2')
binaries_dir = '/DATA/gcc-binaries'
elfshaker_bin = '/home/marxin/Programming/elfshaker/target/release/elfshaker'
elfshaker_repo = Path('/home/marxin/elfshaker-gcc-binaries')
elfshaker_packs = elfshaker_repo / 'elfshaker_data' / 'packs'
tmpdir = Path('/dev/shm/tmp-elfshaker')

revisions = [x.hexsha for x in reversed(list(repo.iter_commits(last_revision + '..origin/master', first_parent=True)))]
print(f'Have: {len(revisions)} revisions')

revisions = [hexsha for hexsha in revisions if Path(binaries_dir, f'{hexsha}.tar.zst').exists()]
revcount = len(revisions)
print(f'Have: {revcount} revisions with existing tarball')

shutil.rmtree(elfshaker_repo, ignore_errors=True)
elfshaker_packs.mkdir(parents=True)

shutil.rmtree(tmpdir, ignore_errors=True)
tmpdir.mkdir(parents=True)


def detect_file_metainfo(folder):
    symlinks = {}
    executables = []

    for root, _, files in os.walk(folder):
        for file in files:
            path = Path(root, file)
            if path.is_symlink():
                symlinks[str(path)] = str(path.readlink())
            if path.stat().st_mode & stat.S_IXUSR:
                executables.append(str(path))

    return {'symlinks': symlinks, 'executables': sorted(executables)}


def pack_revisions(n, revisions):
    if n < 4:
        delay = 30 * n
        print(f'Sleeping for {delay} s', flush=True)
        time.sleep(delay)
        print(f'Starting {n} after sleeping')

    start = time.monotonic()
    tempdir = tempfile.mkdtemp(dir=tmpdir)
    os.chdir(tempdir)
    print(f'Packing {n} in {tempdir}')
    for h in revisions:
        archive = f'{h}.tar'
        zstd_archive = f'{archive}.zst'
        abs_zstd_archive = f'{binaries_dir}/{zstd_archive}'
        if Path(abs_zstd_archive).exists():
            shutil.copyfile(abs_zstd_archive, zstd_archive)
            subprocess.check_output(f'zstd -T0 -d {zstd_archive} -f', shell=True, stderr=subprocess.DEVNULL)
            subprocess.check_output(f'tar xvf {archive}', shell=True)
            os.remove(archive)
            os.remove(zstd_archive)
            with open('meta.json', 'w') as meta:
                metadata = detect_file_metainfo('.')
                json.dump(metadata, meta, indent=2)
            subprocess.check_output(f'/home/marxin/Programming/elfshaker/target/release/elfshaker store {h}',
                                    shell=True)

    packname = f'pack-{n:04}'
    subprocess.check_output(f'{elfshaker_bin} pack {packname} --compression-level {COMPRESSION_LEVEL}',
                            shell=True, stderr=subprocess.PIPE)
    shutil.copy(f'elfshaker_data/packs/{packname}.pack', elfshaker_packs)
    shutil.copy(f'elfshaker_data/packs/{packname}.pack.idx', elfshaker_packs)
    shutil.rmtree(tempdir)
    print(f'Packing {n} took {time.monotonic() - start:.2f}')


with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
    futures = []
    for i in range(revcount // CHUNK_SIZE):
        chunk = revisions[:CHUNK_SIZE]
        futures.append(executor.submit(pack_revisions, i, chunk))
        revisions = revisions[CHUNK_SIZE:]
    concurrent.futures.wait(futures)
    for future in futures:
        future.result()
