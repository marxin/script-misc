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

RELEASES = """
372a443092ee1656c6d866a16e6da6df32b1f71d
6c53ef36e5bfe222e9786cd0b2afe90784a8a43d
3cf2083d636bab3e3a6e91e8b0a0ca1244dff722
b70261df79330539a127c5bee7b4bf61cf029dd5
5ab2fe5755fdcbca49bb1c0dedb9d77cb26a13b0
2da13f5a051c8a28a85311fea990355b4797c179
ade89f291493b5e697047441c1193e5fc8278d3e
fc567ceb717bbcfc3ae0a02a193bcb34d95362ee
c8be0366b55cdb3233abcf79abe2c5ddc6f82cb9
52d80075bc3cc4270756284258400a116528ea7c
4f18db57daffc62a373e30d93c9552f2b94adf09
ea29f0882c0cb710b0444744eaf368cf0143d7a0
0c1af5b6fde830146e5003b018ebabd2095533f4
7a5558ee1c57939c34d0d9a337b26533c94a75e2
c8898526d699174304c71ad2c2f0805bf7e27d93
926d9947847a0683cf34de6fc231209747576088
a9425683787eeba7b9a4bb6c36588885160ab1f1
4cf01c09fe137b7a70b9879ca396823615962eb3
91c632c88994dca583bcd94e39cd3eba1506ecfe
abaef5489e27672c45aa05f41ea7ed52f3fa2748
e31ae982c446804d1b259554203401392b078364
303f81ad7e9f278d5ea5a8bd4193ed9da76bc251
586a0829dc38626ca27b79e5dd689fae32fc8ca8
6184085fc664265dc78fd1ad4204c0cbef202628
adafdb1e7212d53a0ff4c58f0f42dc96200affbb
b2d961e7342b5ba4e57adfa81cb189b738d10901
406c2abec3f998e9064919b22db62f38a7c0e7b9
ddeb81e76461fc0075542d436dc962f3cf6fac92
4c44b708f11eec6fc02456e8577708d01ca92327
8cd3bffead2ed1d1998c190865694f920fbc93ab
eafe83f2f20ef0c1e7703c361ba314b44574523c
c8913260b0756f977ab5e6e6392c51a83657fffc
a0c06cc27d2146b7d86758ffa236516c6143d62c
4212a6a3e44f870412d9025eeb323fd4f50a61da
13c83c4cc679ad5383ed57f359e53e8d518b7842
7a15b5060a83ea8282323d92043c6152e6a3e22d
6e6e3f144a33ae504149dc992453b4f6dea12fdb
ee5c3db6c5b2c3332912fb4c9cfa2864569ebd9a
f00b5710a30f22efc3171c393e56aeb335c3cd39
7ff47281ce4f3699185b06a3430968eac2a5b0c6
50bc9185c2821350f0b785d6e23a6e9dcde58466
7ca388565af176bd4efd4f8db1e5e9e11e98ef45
2d280e7eafc086e9df85f50ed1a6526d6a3a204d
1ea978e3066ac565a1ec28a96a4d61eaf38e2726
2ee5e4300186a92ad73f1a1a64cb918dc76c8d67
"""


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
