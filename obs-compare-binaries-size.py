#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import tempfile
import json

from termcolor import colored

parser = argparse.ArgumentParser(description = 'OBS compare binary sizes')
parser.add_argument('source', help = 'Folder with source JSON files')
parser.add_argument('target', help = 'Folder with target JSON files')
args = parser.parse_args()

all_sections = ['normal', 'devel', 'debug']

branched = set('000product,000release-packages,00aggregates,alsa,ant,apparmor,argyllcms,augeas,bootstrap-copy,btrfsprogs,cdrdao,ceph,ceph-test,clutter,cmocka,cppunit,cross-aarch64-gcc7,cross-arm-gcc7,cross-arm-none-gcc7,cross-arm-none-gcc7-bootstrap,cross-avr-gcc7,cross-avr-gcc7-bootstrap,cross-epiphany-gcc7,cross-epiphany-gcc7-bootstrap,cross-hppa-gcc7,cross-i386-gcc7,cross-m68k-gcc7,cross-mips-gcc7,cross-nvptx-gcc7,cross-ppc64-gcc7,cross-ppc64le-gcc7,cross-rx-gcc7,cross-rx-gcc7-bootstrap,cross-s390x-gcc7,cross-sparc-gcc7,cross-sparc64-gcc7,cross-x86_64-gcc7,device-mapper,fabtests,ffmpeg-4,flatpak,fuse,fwupd,gcc,gcc7,gcc7-AGGR,gcc7-testresults,gcc9,gdb,glib2,glusterfs,gnome-settings-daemon,gperftools,grub2,gtk3,infinipath-psm,java-11-openjdk,java-1_8_0-openjdk,java-cup-bootstrap,javacc,jemalloc,kdepim-runtime,kjsembed,kross,leveldb,libaio,libapparmor,libbsd,libfabric,libimagequant,liboil,libostree,libqt4,libqt4-sql-plugins,libqt5-qtbase,libqt5-qtscript,libqt5-qttools,libqt5-qtwebkit,libreiserfs,libreoffice,libselinux-bindings,libsigsegv,libvirt,libvpx,lksctp-tools,llvm6,llvm7,ltrace,lvm2,lvm2-clvm,lzo,malaga-suomi,mariadb,Mesa,Mesa-drivers,mono-core,MozillaThunderbird,multipath-tools,mutter,numactl,ocaml-ocamlbuild,open-isns,open-lldp,openucx,papi,pcp,pcre2,php7,pmdk,protobuf,protobuf-c,pulseaudio,python-base,python-doc,python-numpy,python-semanage,python3-libmount,qemu,qemu-linux-user,qemu-testsuite,rdma-core,reiserfs,rpmlint-mini,rpmlint-mini-AGGR,rust,sanlock,shim,squashfs,strace,texlive,util-linux,util-linux-systemd,valgrind,vim,virtualbox,vlc,webkit2gtk3,xen,xerces-j2,xf86-video-intel,xorg-x11-server,xterm,xtrabackup,yast2-theme-SLE,zstd,projectM'.split(','))
branched = set()

def get_section_name(rpm):
    if '-debuginfo-' in rpm or '-debug-' in rpm:
        return 'debug'
    elif '-devel-' in rpm:
        return 'devel'
    else:
        return 'normal'

def get_canon_rpm_name(name):
    name = name[:name.rfind('-')]
    return name.replace('/bins2/', '/bins/')

def get_canon_filename(name):
    if name.endswith('i386.debug') or name.endswith('x86_64.debug'):
       name = name[:name.rfind('-')]
    return name.replace('/bins2/', '/bins/')

def strip_path(path):
    token = 'bins'
    return path[path.find(token) + len(token) + 1:]

def strip_json(path):
    t = '.json'
    assert path.endswith(t)
    return path[:-len(t)]

class Rpm:
    def __init__(self, data):
        self.name = data['name']
        self.canoname = get_canon_rpm_name(self.name)
        self.size = data['size']
        self.extracted_size = data['extracted_size']
        self.files = dict(data['files'])
        self.canonfiles = dict((get_canon_filename(x[0]), x[1]) for x in data['files'])
        assert len(self.files.keys()) == len(self.canonfiles.keys())

class Package:
    def __init__(self, data):
        self.name = data['name']
        self.sections = {}
        for s in all_sections:
            self.sections[s] = []

        for k, v in data['sections'].items():
            for rpm in v:
                section = get_section_name(rpm['name'])
                self.sections[section].append(Rpm(rpm))

    def get_rpm_by_name(self, section_name, name):
        for rpm in self.sections[section_name]:
            if rpm.canoname == name:
                return rpm

        return None

    def compare_sections(self, section_name, other):
        for rpm in self.sections[section_name]:
            if other.get_rpm_by_name(section_name, rpm.canoname) == None:
                return False

        return True

    def compare_files(self, section_name, package, other, report):
        for rpm in self.sections[section_name]:
            other_rpm = other.get_rpm_by_name(section_name, rpm.canoname)
            if other_rpm != None:
                for f in rpm.files.keys():
                    cn = get_canon_filename(f)
                    if cn in other_rpm.canonfiles:
                        report.append((strip_path(f), strip_path(rpm.name), strip_json(package), rpm.files[f], other_rpm.canonfiles[cn]))
                    else:
                        pass
                        #print(cn)

    def get_rpm_total_size(self, section_name):
        return sum([r.size for r in self.sections[section_name]])

    def get_rpm_total_extracted_size(self, section_name):
        return sum([r.extracted_size for r in self.sections[section_name]])

def parse_files(folder):
    d = {}
    for f in os.listdir(folder):
        d[f] = Package(json.load(open(os.path.join(folder, f))))
    return d

source_files = parse_files(args.source)
target_files = parse_files(args.target)

print('Total: %s' % (len(source_files)))
print('Branched packages to skip: %d' % len(branched))

for type in all_sections:
    todo = []
    for s, s2 in source_files.items():
        name = strip_json(s)
        if name in branched:
#            print('Ignoring branched: %s' % name)
            continue
        if 'kernel' in s:
            continue
        if not s in target_files:
            print('Missing in target: ' + s)
        else:
            c = s2.compare_sections(type, target_files[s])
            if c != True:
                print('Different RPM names: %s: %d' % (s, c))
            else:
                todo.append(s)

    print('Same RPM files: %s' % (len(todo)))
    package_diff = []
    for s in sorted(todo):
        s1 = source_files[s].get_rpm_total_size(type)
        if s1 == 0:
            continue
        s2 = target_files[s].get_rpm_total_size(type)
        s3 = source_files[s].get_rpm_total_extracted_size(type)
        s4 = target_files[s].get_rpm_total_extracted_size(type)
        item = (strip_json(s), s1, s2, s3, s4)
        package_diff.append(item)

    with open('report/packages-%s.csv' % type, 'w+') as of:
        of.write('Package,RPM size before,RPM size after,Extracted size before,Extracted size after\n')
        for p in package_diff:
            of.write(','.join([str(x) for x in p]))
            of.write('\n')

    file_comparison = []
    for s in sorted(todo):
        source_files[s].compare_files(type, s, target_files[s], file_comparison)

    with open('report/files-%s.csv' % type, 'w+') as of:
        of.write('File,RPM,Package,Size before,Size after\n')
        for p in file_comparison:
            of.write(','.join([str(x) for x in p]))
            of.write('\n')

