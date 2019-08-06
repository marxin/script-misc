#!/usr/bin/env python3

import os
import subprocess
import shutil

source = '/home/marxin/Downloads/rpms-no-lto/x86_64/'
target = '/home/marxin/Downloads/rpms-with-lto/x86_64/'

binfolder = os.path.join('/dev/shm/rpm')

def clean():
    shutil.rmtree(binfolder, ignore_errors = True)
    os.mkdir(binfolder)

def process_rpm(full):
    clean()
    subprocess.run('rpm2cpio %s | cpio -idmv -D %s' % (full, binfolder),
            shell = True, stderr = subprocess.PIPE)

    candidates = set()
    for r, dirs, files in os.walk(binfolder):
        for f in files:
            a = os.path.realpath(os.path.join(r, f))
            if os.path.exists(a):
                candidates.add(a)
            else:
                # TODO
                pass

    d = {}
    for f in candidates:
        r = subprocess.run('timeout 3 file %s' % f, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = 'utf8')
        if 'ELF' in r.stdout:
            d[f] = get_filesize(f)

    return d

def get_filesize(path):
    return os.stat(path).st_size

def get_source_by_rpm_name(rpm):
    parts = rpm.split('.')[:-4]
    prefix = '.'.join(parts)
    for rpm in os.listdir(source):
        if rpm.startswith(prefix):
            return rpm
    return None

rpms = []

for rpm in sorted(os.listdir(target)):
    rpm2 = get_source_by_rpm_name(rpm)
    if rpm2:
        rpms.append((rpm, rpm2))

target_total = 0
source_total = 0

for rpm in rpms:
    target_total += get_filesize(os.path.join(target, rpm[0]))
    source_total += get_filesize(os.path.join(source, rpm[1]))

print('RPM total size before: %d' % source_total)
print('RPM total size after: %d' % target_total)

target_total = 0
source_total = 0
filecount = 0

for i, rpm in enumerate(rpms):
    target_data = process_rpm(os.path.join(target, rpm[0]))
    source_data = process_rpm(os.path.join(source, rpm[1]))

    for key, value in target_data.items():
        if key in source_data:
            source_total += source_data[key]
            target_total += value
            filecount += 1
        else:
            print('   missing: %s' % key)

    print('%d/%d:%s:%d:%d' % (i, len(rpms), rpm[0], len(target_data.items()), len(source_data.items())))

print('')
print('Files processed: %d' % filecount)
print('ELF files total before: %d' % source_total)
print('ELF files total after: %d' % target_total)
