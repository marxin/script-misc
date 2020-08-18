#!/usr/bin/env python3

import subprocess
import tempfile
import psutil
import os

targets = '''
aarch64-elf
aarch64-linux
aarch64_be-linux-gnu_ilp32
alpha-dec-vms
alpha-linux
alpha-linuxecoff
alpha-netbsd
alpha-unknown-freebsd4.7
am33_2.0-linux
arc-elf
arc-linux-uclibc
arm-elf
arm-linuxeabi
arm-nacl
arm-netbsdelf
arm-nto
arm-pe
arm-symbianelf
arm-vxworks
arm-wince-pe
armeb-linuxeabi
avr-elf
bfin-elf
bfin-linux-uclibc
bpf-none
cr16-elf
cris-elf
cris-linux
crisv32-linux
crx-elf
csky-elf
csky-linux
d10v-elf
d30v-elf
dlx-elf
epiphany-elf
fr30-elf
frv-elf
frv-linux
ft32-elf
h8300-elf
h8300-linux
hppa-hp-hpux10
hppa-linux
hppa64-hp-hpux11.23
hppa64-linux
i386-bsd
i386-darwin
i386-lynxos
i386-msdos
i586-linux
i686-nto
i686-pc-beos
i686-pc-elf
i686-pe
i686-vxworks
ia64-elf
ia64-freebsd5
ia64-hpux
ia64-linux
ia64-netbsd
ia64-vms
ip2k-elf
iq2000-elf
lm32-elf
lm32-linux
m32c-elf
m32r-elf
m32r-linux
m68hc11-elf
m68hc12-elf
m68k-elf
m68k-linux
mcore-elf
mcore-pe
mep-elf
metag-linux
microblaze-elf
microblaze-linux
mips-linux
mips-sgi-irix6
mips-vxworks
mips64-linux
mips64-openbsd
mips64el-openbsd
mipsel-linux-gnu
mipsisa32el-linux
mipstx39-elf
mmix
mn10200-elf
mn10300-elf
moxie-elf
msp430-elf
mt-elf
nds32be-elf
nds32le-linux
nios2-linux
ns32k-netbsd
ns32k-pc532-mach
or1k-elf
or1k-linux
pdp11-dec-aout
pj-elf
powerpc-aix5.1
powerpc-aix5.2
powerpc-eabisim
powerpc-eabivle
powerpc-freebsd
powerpc-linux
powerpc-nto
powerpc-wrs-vxworks
powerpc64-freebsd
powerpc64-linux
powerpc64le-linux
powerpcle-elf
pru-elf
riscv32-elf
riscv64-linux
rl78-elf
rs6000-aix4.3.3
rs6000-aix5.1
rs6000-aix5.2
rx-elf
s12z-elf
s390-linux
s390x-linux
score-elf
sh-linux
sh-nto
sh-pe
sh-rtems
sh-vxworks
shle-unknown-netbsdelf
sparc-elf
sparc-linux
sparc-sun-solaris2
sparc-vxworks
sparc64-linux
spu-elf
tic30-unknown-coff
tic4x-coff
tic54x-coff
tic6x-elf
tilegx-linux
tilepro-linux
v850-elf
vax-netbsdelf
visium-elf
wasm32
x86_64-cloudabi
x86_64-linux
x86_64-pc-linux-gnux32
x86_64-rdos
x86_64-w64-mingw32
xgate-elf
xstormy16-elf
xtensa-elf
z80-coff
z80-elf
z8k-coff
'''

targets = targets.strip().split('\n')
cpu_count = psutil.cpu_count()

for i, target in enumerate(targets):
    print('%d/%d: %s' % (i, len(targets), target))
    folder = tempfile.TemporaryDirectory(prefix='/dev/shm/')
    os.chdir(folder.name)
    subprocess.check_output('~/Programming/binutils/configure --build=x86_64-linux --disable-nls --disable-gdb --disable-gdbserver --disable-sim --disable-readline --disable-libdecnumber --enable-obsolete --target=%s'
            % target, shell=True, stderr=subprocess.DEVNULL)
    subprocess.check_output('make -j%d' % cpu_count, shell=True, stderr=subprocess.DEVNULL)
    subprocess.run('make check -k -j%d' % cpu_count, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    output = subprocess.check_output('find .  -name "*.log" | xargs grep "^FAIL" | sort', shell=True, stderr=subprocess.DEVNULL, encoding='utf8').strip()
    if output:
        errors = len(output.split('\n'))
        print('test errors: %d' % errors)
        print(output)
    folder.cleanup()
