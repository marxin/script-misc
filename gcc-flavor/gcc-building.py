#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import os

from datetime import datetime

parser = argparse.ArgumentParser(description='Batch GCC builder.')
parser.add_argument('repository', help = 'GCC repository')
parser.add_argument('install', help = 'Install prefix')
parser.add_argument('tmp', help = 'TMP folder')

args = parser.parse_args()

configurations = (('system-O2-generic', 'bootstrap-debug', '--disable-bootstrap', ''),
    ('system-O2-native', 'bootstrap-debug-native', '--disable-bootstrap', ''),
    ('bootstrap-O2-generic', 'bootstrap-debug', '', ''),
    ('bootstrap-O2-native', 'bootstrap-debug-native', '', ''),
    ('lto-bootstrap-O2-generic', 'bootstrap-lto', '', ''),
    ('lto-bootstrap-O2-native', 'bootstrap-lto-native', '', ''),
    ('pgo-bootstrap-O2-generic', 'bootstrap-debug', '', 'profiledbootstrap'),
    ('pgo-bootstrap-O2-native', 'bootstrap-debug-native', '', 'profiledbootstrap'),
    ('pgo-lto-bootstrap-O2-generic', 'bootstrap-lto', '', 'profiledbootstrap'),
    ('pgo-lto-bootstrap-O2-native', 'bootstrap-lto-native', '', 'profiledbootstrap')
    )

shutil.rmtree(args.install, ignore_errors = True)
os.mkdir(args.install)

for i, c in enumerate(configurations):
    print('Doing %s: %d of %d' % (c[0], i + 1, len(configurations)))
    start = datetime.now()

    shutil.rmtree(args.tmp, ignore_errors = True)
    os.mkdir(args.tmp)

    os.chdir(args.tmp)

    l = open(os.path.join(args.install, c[0] + '.log'), 'w')
    subprocess.call(os.path.join(args.repository, 'configure') + ' --enable-checking=release --disable-werror --disable-multilib --disable-libsanitizer --with-build-config=' + c[1] + ' ' + c[2] + ' --prefix=' + os.path.join(args.install, c[0]), shell = True,
            stdout = l, stderr = l) == 0
    assert subprocess.call('make -j8 ' + c[3], shell = True, stdout = l, stderr = l) == 0
    assert subprocess.call('make install', shell = True, stdout = l, stderr = l) == 0

    print('Took me: %s' % str(datetime.now() - start))
