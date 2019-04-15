#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import tempfile
import json

from termcolor import colored

parser = argparse.ArgumentParser(description = 'OBS hacking')
parser.add_argument('project', help = 'OBS project name')
parser.add_argument('project2', help = 'OBS project name')
parser.add_argument('repository', help = 'OBS repository')
parser.add_argument('tmp', help = 'TMP folder where to extract RPM packages')
parser.add_argument('output_folder', help = 'Output folder where to save. json files')
args = parser.parse_args()

result = subprocess.check_output('osc r %s -r %s -a %s --csv' % (args.project, args.repository, 'x86_64'), shell = True)
packages = result.decode('utf-8', 'ignore').strip().split('\n')
packages = [x.split(';')[0] for x in packages if 'succeeded' in x]
packages = [x for x in packages if x != '_' and not 'gcc' in x]

branched = set('000product,000release-packages,00aggregates,alsa,ant,apparmor,argyllcms,augeas,bootstrap-copy,btrfsprogs,cdrdao,ceph,ceph-test,clutter,cmocka,cppunit,cross-aarch64-gcc7,cross-arm-gcc7,cross-arm-none-gcc7,cross-arm-none-gcc7-bootstrap,cross-avr-gcc7,cross-avr-gcc7-bootstrap,cross-epiphany-gcc7,cross-epiphany-gcc7-bootstrap,cross-hppa-gcc7,cross-i386-gcc7,cross-m68k-gcc7,cross-mips-gcc7,cross-nvptx-gcc7,cross-ppc64-gcc7,cross-ppc64le-gcc7,cross-rx-gcc7,cross-rx-gcc7-bootstrap,cross-s390x-gcc7,cross-sparc-gcc7,cross-sparc64-gcc7,cross-x86_64-gcc7,device-mapper,fabtests,ffmpeg-4,flatpak,fuse,fwupd,gcc,gcc7,gcc7-AGGR,gcc7-testresults,gcc9,gdb,glib2,glusterfs,gnome-settings-daemon,gperftools,grub2,gtk3,infinipath-psm,java-11-openjdk,java-1_8_0-openjdk,java-cup-bootstrap,javacc,jemalloc,kdepim-runtime,kjsembed,kross,leveldb,libaio,libapparmor,libbsd,libfabric,libimagequant,liboil,libostree,libqt4,libqt4-sql-plugins,libqt5-qtbase,libqt5-qtscript,libqt5-qttools,libqt5-qtwebkit,libreiserfs,libreoffice,libselinux-bindings,libsigsegv,libvirt,libvpx,lksctp-tools,llvm6,llvm7,ltrace,lvm2,lvm2-clvm,lzo,malaga-suomi,mariadb,Mesa,Mesa-drivers,mono-core,MozillaThunderbird,multipath-tools,mutter,numactl,ocaml-ocamlbuild,open-isns,open-lldp,openucx,papi,pcp,pcre2,php7,pmdk,protobuf,protobuf-c,pulseaudio,python-base,python-doc,python-numpy,python-semanage,python3-libmount,qemu,qemu-linux-user,qemu-testsuite,rdma-core,reiserfs,rpmlint-mini,rpmlint-mini-AGGR,rust,sanlock,shim,squashfs,strace,texlive,util-linux,util-linux-systemd,valgrind,vim,virtualbox,vlc,webkit2gtk3,xen,xerces-j2,xf86-video-intel,xorg-x11-server,xterm,xtrabackup,yast2-theme-SLE,zstd,projectM'.split(','))

branched = set('projectM'.split(','))
print('Successfull packages: %d: %s' % (len(packages), str(packages)))

binfolder = args.tmp
assert '/dev/shm' in binfolder
root = os.path.join(binfolder, 'root')

def clean():
    shutil.rmtree(binfolder, ignore_errors = True)
    os.mkdir(binfolder)

def cleanroot():
    shutil.rmtree(root, ignore_errors = True)
    os.mkdir(root)

def get_category(rpm):
    if '-devel-' in rpm:
        return 'devel'
    elif '-debuginfo-' in rpm or '-debug-' in rpm:
        return 'debug'
    else:
        return 'normal'

def process_rpm(full):
    cleanroot()
    vm = {'name': full, 'size': os.path.getsize(full), 'files': []} 

    subprocess.check_output('rpm2cpio %s | cpio -idmv -D %s' % (full, root), shell = True, stderr = subprocess.PIPE)

    r = subprocess.check_output('du -bs %s' % root, shell = True, encoding = 'utf8')
    value = int(r.strip().split('\t')[0])
    vm['extracted_size'] = value
    print('  extracting: %s: %d' % (full, value))

    # process all files
    candidates = set()
    for r, dirs, files in os.walk(root):
        for f in files:
            a = os.path.realpath(os.path.join(r, f))
            if os.path.exists(a):
                candidates.add(a)
            else:
                # TODO
                pass

    elfs = []
    for f in candidates:
        r = subprocess.run('file %s' % f, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = 'utf8')
        if 'ELF' in r.stdout:
            s = os.path.getsize(f)
            vm['files'].append((f, s))
            print('    file: %s: %d' % (f, s))

    return vm

def process_category(name):
    vm = []
    for f in os.listdir(binfolder):
        full = os.path.join(binfolder, f)
        if f.endswith('.rpm') and get_category(f) == name:
            vm.append(process_rpm(full))

    return vm

for i, p in enumerate(packages):
    if p in branched:
        print('Skipping, branched: %s' % p)
        continue

    print('Downloading: %s (%d/%d)' % (p, i, len(packages)))
    jsonfile = os.path.join(args.output_folder, p + '.json')
    if os.path.exists(jsonfile):
        continue

    clean()
    try:
        vm = {'name': p, 'sections': {}}
        subprocess.check_output('osc getbinaries %s %s %s x86_64 --debug -d %s' % (args.project2, p, args.repository, binfolder), shell = True, stderr = subprocess.PIPE)
        vm['sections']['normal'] = process_category('normal')
        vm['sections']['devel'] = process_category('devel')
        vm['sections']['debug'] = process_category('debug')
        with open(jsonfile, 'w') as of:
            json.dump(vm, of)
        
    except subprocess.CalledProcessError as e:
        print(str(e))
