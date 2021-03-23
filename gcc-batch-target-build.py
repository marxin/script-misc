#!/usr/bin/env python3

import argparse
import concurrent.futures
import os
import shutil
import subprocess


default_targets = """aarch64-elf aarch64-linux-gnu aarch64-rtems
  alpha-linux-gnu alpha-netbsd alpha-openbsd
  alpha64-dec-vms alpha-dec-vms
  amdgcn-amdhsa
  arc-elf32OPT-with-cpu=arc600 arc-elf32OPT-with-cpu=arc700
  arc-linux-uclibcOPT-with-cpu=arc700 arceb-linux-uclibcOPT-with-cpu=arc700
  arm-netbsdelf
  arm-linux-androideabi arm-uclinux_eabi arm-eabi arm-rtems
  arm-symbianelf avr-elf
  bfin-elf bfin-uclinux bfin-linux-uclibc bfin-rtems bfin-openbsd
  bpf-unknown-none
  c6x-elf c6x-uclinux cr16-elf cris-elf
  csky-elf csky-linux-gnu
  epiphany-elf epiphany-elfOPT-with-stack-offset=16 fido-elf
  fr30-elf frv-elf frv-linux ft32-elf h8300-elf hppa-linux-gnu
  hppa-linux-gnuOPT-enable-sjlj-exceptions=yes hppa64-linux-gnu
  hppa2.0-hpux10.1 hppa64-hpux11.3
  hppa64-hpux11.0OPT-enable-sjlj-exceptions=yes hppa2.0-hpux11.9
  i686-pc-linux-gnu i686-apple-darwin i686-apple-darwin9 i686-apple-darwin10
  i486-freebsd4 i686-freebsd6 i686-kfreebsd-gnu
  i686-netbsdelf9
  i686-openbsd i686-elf i686-kopensolaris-gnu i686-symbolics-gnu
  i686-pc-msdosdjgpp i686-lynxos i686-nto-qnx
  i686-rtems i686-solaris2.11 i686-wrs-vxworks
  i686-wrs-vxworksae
  i686-cygwinOPT-enable-threads=yes i686-mingw32crt ia64-elf
  ia64-freebsd6 ia64-linux ia64-hpux ia64-hp-vms iq2000-elf lm32-elf
  lm32-rtems lm32-uclinux m32c-rtems m32c-elf m32r-elf m32rle-elf
  m32r-linux m32rle-linux m68k-elf m68k-netbsdelf
  m68k-openbsd m68k-uclinux m68k-linux m68k-rtems
  mcore-elf microblaze-linux microblaze-elf
  mips-netbsd
  mips64el-st-linux-gnu mips64octeon-linux mipsisa64r2-linux
  mipsisa32r2-linux-gnu mipsisa64r2-sde-elf mipsisa32-elfoabi
  mipsisa64-elfoabi mipsisa64r2el-elf mipsisa64sr71k-elf mipsisa64sb1-elf
  mipsel-elf mips64-elf mips64vr-elf mips64orion-elf mips-rtems
  mips-wrs-vxworks mipstx39-elf mmix-knuth-mmixware mn10300-elf moxie-elf
  moxie-uclinux moxie-rtems
  msp430-elf msp430-elfbare
  nds32le-elf nds32be-elf
  nios2-elf nios2-linux-gnu nios2-rtems
  nvptx-none
  or1k-elf or1k-linux-uclibc or1k-linux-musl or1k-rtems
  pdp11-aout
  powerpc-darwin8
  powerpc-darwin7 powerpc64-darwin powerpc-freebsd6 powerpc-netbsd
  powerpc-eabisimaltivec powerpc-eabisim ppc-elf
  powerpc-eabialtivec powerpc-xilinx-eabi powerpc-eabi
  powerpc-rtems
  powerpc64-linux_altivec
  powerpc-wrs-vxworks powerpc-wrs-vxworksae powerpc-wrs-vxworksmils
  powerpc-lynxos powerpcle-elf
  powerpcle-eabisim powerpcle-eabi
  pru-elf
  riscv32-unknown-linux-gnu riscv64-unknown-linux-gnu
  rs6000-ibm-aix6.1 rs6000-ibm-aix7.1
  rl78-elf rx-elf s390-linux-gnu s390x-linux-gnu s390x-ibm-tpf sh-elf
  shle-linux sh-netbsdelf sh-superh-elf
  sh-rtems sh-wrs-vxworks sparc-elf
  sparc-leon-elf sparc-rtems sparc-linux-gnu
  sparc-leon3-linux-gnuOPT-enable-target=all sparc-netbsdelf
  sparc64-sun-solaris2.11OPT-with-gnu-ldOPT-with-gnu-asOPT-enable-threads=posix
  sparc-wrs-vxworks sparc64-elf sparc64-rtems sparc64-linux sparc64-freebsd6
  sparc64-netbsd sparc64-openbsd
  tilegx-linux-gnuOPT-enable-obsolete tilegxbe-linux-gnuOPT-enable-obsolete
  tilepro-linux-gnuOPT-enable-obsolete
  v850e1-elf v850e-elf v850-elf v850-rtems vax-linux-gnu
  vax-netbsdelf vax-openbsd visium-elf x86_64-apple-darwin
  x86_64-pc-linux-gnuOPT-with-fpmath=avx
  x86_64-elfOPT-with-fpmath=sse x86_64-freebsd6 x86_64-netbsd
  x86_64-w64-mingw32
  x86_64-mingw32OPT-enable-sjlj-exceptions=yes x86_64-rtems
  xstormy16-elf xtensa-elf
  xtensa-linux
"""

JOBS = 4

parser = argparse.ArgumentParser(description='Batch build of GCC binaries')
parser.add_argument('repository', metavar='repository', help='GCC repository')
parser.add_argument('folder', metavar='folder', help='Folder where to build')
parser.add_argument('-t', '--targets', help='Targets to be built (comma separated)')
parser.add_argument('-p', '--preserve', action='store_true', help='Preserve built binaries')
args = parser.parse_args()

targets = [t.strip() for t in default_targets.split(' ') if t]
if args.targets:
    targets = args.targets.split(',')

shutil.rmtree(args.folder, ignore_errors=True)
os.makedirs(args.folder)

log_dir = os.path.join(args.folder, 'logs')
os.makedirs(log_dir)
obj_dir = os.path.join(args.folder, 'objs')
os.makedirs(obj_dir)


def build_target(full_target):
    opts = ''
    target = full_target
    index = full_target.find('OPT')
    if index != -1:
        target = full_target[:index]
        opts = full_target[index + 3:].strip()

    with open(os.path.join(log_dir, full_target + '.stderr.log'), 'w') as err:
        with open(os.path.join(log_dir, full_target + '.stdout.log'), 'w') as out:
            d = os.path.join(obj_dir, full_target)
            os.mkdir(d)
            os.chdir(d)

            # 1) configure
            cmd = ('%s --target=%s --disable-bootstrap --enable-languages=c,c++ --disable-multilib %s --enable-obsolete'
                   % (os.path.join(args.repository, 'configure'), target, opts))
            cmd = cmd.strip()
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if r.returncode != 0:
                print(f'Configure FAILED for {full_target}')
                return

            out.write(r.stdout.decode('utf-8'))
            err.write(r.stderr.decode('utf-8'))

            # 2) build
            cmd = f'nice make -j{JOBS} all-host CXXFLAGS="-O0 -g" CFLAGS="-O0 -g"'
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, encoding='utf8')
            if r.returncode != 0:
                print(f'Target failed: {full_target}')

            out.write(r.stdout)
            err.write(r.stderr)

            # remove objdir if OK
            if r.returncode == 0 and not args.preserve:
                shutil.rmtree(d)
            print('D', end='', flush=True)


print(f'Total targets: {len(targets)}')
print('.' * len(targets))
with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = []
    for t in targets:
        futures.append(executor.submit(build_target, t))
    concurrent.futures.wait(futures)
    for future in futures:
        if future.exception():
            print(future.exception())
    print()
