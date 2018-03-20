#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import os
import time

from datetime import datetime

DEVNULL = open(os.devnull, 'wb')

parser = argparse.ArgumentParser(description='Batch postgres speed tester')
parser.add_argument('source', help = 'Source files of postgres')
parser.add_argument('install', help = 'Install prefix')
parser.add_argument('pgdata', help = 'Postgres data')

args = parser.parse_args()

def get_tps(n):
    result = subprocess.check_output(os.path.join(args.install, 'usr/local/pgsql/bin/pgbench') + ' -h localhost -t %d -v' % n, shell = True, stderr = DEVNULL, encoding = 'utf8')
    lines = [x.strip() for x in result.split('\n')]
    for l in lines:
        if l.startswith('tps'):
            return float(l.split(' ')[2])

def build(flags, my_env):
    print(' - building with flags: ' + flags)
    shutil.rmtree(args.install, ignore_errors = True)

    os.chdir(args.source)

    subprocess.check_output('./configure', shell = True, env = my_env)
    subprocess.check_output('make clean', shell = True, stderr = DEVNULL, env = my_env)
    subprocess.check_output('make -j8', shell = True, stderr = DEVNULL, env = my_env)

def install_and_test(name, only_make_check = False, print_it = True):
    if only_make_check:
        print(' - running make check')
        subprocess.check_output('make check', shell = True)
        return

    print(' - running PSGQL test')
    subprocess.check_output('make install DESTDIR=' + args.install, shell = True)

    shutil.rmtree(args.pgdata, ignore_errors = True)
    os.mkdir(args.pgdata, 0o700)
    subprocess.check_output(os.path.join(args.install, 'usr/local/pgsql/bin/initdb') + ' ' + args.pgdata, shell = True)

    print('Starting PGSQL server')
    server = subprocess.Popen([os.path.join(args.install, 'usr/local/pgsql/bin/postgres'), '-D', args.pgdata], stderr = DEVNULL)
    time.sleep(1)

    subprocess.check_output(os.path.join(args.install, 'usr/local/pgsql/bin/createdb') + ' marxin -h localhost', shell = True)

    start = datetime.now()
    subprocess.check_output(os.path.join(args.install, 'usr/local/pgsql/bin/pgbench') + ' -i  -h localhost -p 5432 -U marxin -s 100', stderr = DEVNULL, shell = True)
    duration = datetime.now() - start

    if print_it:
        print('DB init took: %.2f' % duration.total_seconds())

    values = []
    runs = 10
    for i in range(runs):
        values.append(get_tps(10000))

    if print_it:
        print('average TPS:%s:%.2f' % (name, (sum(values) / len(values))))
        print('Killing server')
    server.kill()

def build_and_test(flags, pgo = False, train_full = False, compiler = None, libs = None):
    name = flags
    if pgo:
        name += ' PGO'
    if train_full:
        name += ' reference TRAIN'

    if compiler != None:
        name = 'GCC 8:' + name

    my_env = os.environ.copy()
    my_env['CFLAGS'] = flags
    my_env['CXXFLAGS'] = flags
    my_env['LDFLAGS'] = flags

    if compiler != None:
        my_env['PATH'] = compiler + ':' + my_env['PATH']
    if libs != None:
        my_env['LD_LIBRARY_PATH'] = libs

    print('=== TESTING: %s, PGO: %d, TRAIN_FULL: %d ===' % (flags, pgo, train_full))
    if pgo:
        subprocess.check_output('git clean -f', shell = True)
        build(flags + ' -fprofile-generate', my_env)
        install_and_test(name, not train_full, False)
        build(flags + ' -fprofile-use', my_env)
        install_and_test(name)
    else:
        build(flags, my_env)
        install_and_test(name)

build_and_test('-O2')
build_and_test('-O2 -march=native')
build_and_test('-O2 -flto=9')
build_and_test('-O2', True, False)
build_and_test('-O2 -flto=9')
build_and_test('-O2', True, True)
build_and_test('-O2 -flto=9', True, False)
build_and_test('-O2 -flto=9', True, True)

build_and_test('-O2', compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
build_and_test('-O2 -march=native', compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
build_and_test('-O2 -flto=9', compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
build_and_test('-O2', True, False, compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
build_and_test('-O2 -flto=9', compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
build_and_test('-O2', True, True, compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
build_and_test('-O2 -flto=9', True, False, compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
build_and_test('-O2 -flto=9', True, True, compiler = '/home/marxin/bin/gcc/bin/', libs = '/home/marxin/bin/gcc/lib64/')
