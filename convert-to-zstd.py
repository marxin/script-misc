#!/usr/bin/env python3

import os
import shutil
import subprocess
import filelock

from datetime import datetime

extract_location = '/dev/shm/gcc-bisect-bin/'
install_location = '/home/marxin/DATA/gcc-binaries/'

lock = filelock.FileLock('/tmp/gcc_build_binary.lock')

todo = open('/tmp/all').readlines()

for i, line in enumerate(todo):
    revision = line.strip()
    print('%d/%d: %s' % (i, len(todo), revision))

    archive = os.path.join(install_location, revision + '.7z')
    if os.path.exists(archive):
        with lock:
            shutil.rmtree(extract_location, ignore_errors = True)
            os.mkdir(extract_location)
            start = datetime.now()
            size_before = os.path.getsize(archive)
            cmd = '7z x %s -o%s -aoa' % (archive, extract_location)
            subprocess.check_output(cmd, shell = True)
            tarfile = os.path.join(install_location, revision + '.tar')
            current = os.getcwd()
            os.chdir(extract_location)
            subprocess.check_output('tar cfv %s *' % tarfile, shell = True)
            os.chdir(current)
        subprocess.check_output('zstd --rm -q -19 -T16 %s' % tarfile, shell = True)
        os.remove(archive)
        size_after = os.path.getsize(tarfile + '.zst')
        print((datetime.now() - start).total_seconds())
        print('Size before: %d, after: %d, change: %.2f%%' % (size_before, size_after, 100.0 * size_after / size_before))
