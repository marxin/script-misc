#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path

from git import Repo

git = Path(sys.argv[1]).resolve()
repo = Repo(git)
branches = [11, 12]
objdir = '/dev/shm/myobjdir'
source = '/home/marxin/Programming/tramp3d/tramp3d-v4.ii'
obj = '/tmp/tramp.o'
pwd = os.getcwd()


def clean_temp():
    shutil.rmtree(objdir, ignore_errors=True)


def build_compiler(revision):
    print(f'Building {revision}', flush=True)
    repo.git.checkout(revision)
    clean_temp()
    os.mkdir(objdir)
    os.chdir(objdir)
    subprocess.check_output(f'{git}/configure --enable-languages=c,c++,lto --prefix=/home/marxin/bin/gcc2 '
                            '--disable-multilib --disable-libsanitizer --disable-bootstrap '
                            '--with-ld=`which ld.bfd`', shell=True,
                            stderr=subprocess.DEVNULL)
    subprocess.check_output('make -j`nproc`', shell=True, stderr=subprocess.DEVNULL)


for branch in reversed(branches):
    tip = f'origin/releases/gcc-{branch}'
    basepoint = f'basepoints/gcc-{branch}'
    basepoint_next = f'basepoints/gcc-{branch + 1}~'
    interval = f'{basepoint}..{tip}'
    changes = repo.blame(interval, 'gcc/lto-streamer.h')
    last_bump = None
    for change in changes:
        for line in change[1]:
            if line.startswith('#define LTO_minor_version') or line.startswith('#define LTO_major_version'):
                commit = change[0]
                if not last_bump or commit.committed_datetime > last_bump.committed_datetime:
                    last_bump = commit
    basepoint = repo.commit(basepoint_next)
    assert basepoint.committed_datetime <= last_bump.committed_datetime
    print(f'gcc-{branch} last time bumped in {last_bump}', flush=True)
    build_compiler(tip)
    subprocess.check_output(f'./gcc/xg++ -Bgcc -O2 -c -std=c++98 -flto=16 {source} -o {obj}', shell=True)
    build_compiler(last_bump)
    try:
        subprocess.check_output(f'./gcc/xg++ -Bgcc -O2 -flto=16 {obj} -L ./x86_64-pc-linux-gnu/libstdc++-v3/src/.libs',
                                shell=True)
    finally:
        clean_temp()
