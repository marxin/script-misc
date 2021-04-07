#!/usr/bin/env python3

import subprocess

SRCDIR = '/home/marxin/Programming/gcc'
VERSION = '11.0.1'
OBJDIR = '/dev/shm/objdir'
OUTPUT = '/tmp/gcc-xml'

includes = f'-I{SRCDIR}/gcc/doc -I{SRCDIR}/gcc/doc/include -I{OBJDIR}/gcc'
cmd = 'makeinfo --xml'

subprocess.check_output(f'{cmd} {includes} {SRCDIR}/gcc/doc/gcc.texi -o {OUTPUT}/gcc.xml', shell=True)
subprocess.check_output(f'{cmd} {includes} {SRCDIR}/gcc/fortran/gfortran.texi -I{SRCDIR}/gcc/fortran -o '
                        f'{OUTPUT}/gfortran.xml', shell=True)
subprocess.check_output(f'{cmd} {includes} {SRCDIR}/gcc/go/gccgo.texi -I{SRCDIR}/gcc/go -o {OUTPUT}/gccgo.xml',
                        shell=True)
subprocess.check_output(f'{cmd} {includes} {SRCDIR}/gcc/doc/cpp.texi -o {OUTPUT}/cpp.xml', shell=True)

for lib in ('libgomp', 'libquadmath', 'libitm'):
    subprocess.check_output(f'{cmd} {includes} -I{OBJDIR}/x86_64-pc-linux-gnu/libquadmath/ {SRCDIR}/{lib}/{lib}.texi '
                            f'-o {OUTPUT}/{lib}.xml', shell=True)
subprocess.check_output(f'{cmd} {includes} {SRCDIR}/libffi/doc/libffi.texi -o {OUTPUT}/libffi.xml', shell=True)

subprocess.check_output(f'{cmd} {includes} {SRCDIR}/gcc/doc/gccint.texi -o {OUTPUT}/gccint.xml', shell=True)
subprocess.check_output(f'{cmd} {includes} {SRCDIR}/gcc/doc/cppinternals.texi -o {OUTPUT}/cppinternals.xml', shell=True)
