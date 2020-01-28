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
ignored = set()

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

    def compare_files(self, section_name, package, other, report, total):
        for rpm in self.sections[section_name]:
            other_rpm = other.get_rpm_by_name(section_name, rpm.canoname)
            if other_rpm != None:
                for f in rpm.files.keys():
                    cn = get_canon_filename(f)
                    if cn in other_rpm.canonfiles:
                        size_before = rpm.files[f]
                        size_after = other_rpm.canonfiles[cn]
                        report.append((strip_path(f), strip_path(rpm.name), strip_json(package), to_mb(size_before), to_mb(size_after), round(100.0 * size_after / size_before, 2)))
                        total[3] += size_before
                        total[4] += size_after
                    else:
                        print(cn)
                        pass

    def get_rpm_total_size(self, section_name):
        return sum([r.size for r in self.sections[section_name]])

    def get_rpm_total_extracted_size(self, section_name):
        return sum([r.extracted_size for r in self.sections[section_name]])

def parse_files(folder):
    d = {}
    for f in os.listdir(folder):
        d[f] = Package(json.load(open(os.path.join(folder, f))))
    return d

def to_mb(size):
    return round(size / (1024.0**2), 2)

source_files = parse_files(args.source)
target_files = parse_files(args.target)

print('Total: %s' % (len(source_files)))
print('Branched packages to skip: %d' % len(ignored))

for type in all_sections:
    todo = []
    for s, s2 in source_files.items():
        name = strip_json(s)
        if name in ignored:
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
    total = ['TOTAL', 0, 0, 0, 0]
    for s in sorted(todo):
        s1 = source_files[s].get_rpm_total_size(type)
        if s1 == 0:
            continue
        s2 = target_files[s].get_rpm_total_size(type)
        s3 = source_files[s].get_rpm_total_extracted_size(type)
        s4 = target_files[s].get_rpm_total_extracted_size(type)
        item = (strip_json(s), to_mb(s1), to_mb(s2), to_mb(s3), to_mb(s4), round(100.0 * s2 / s1, 2), round(100.0 * s4 / s3, 2))
        package_diff.append(item)
        total[1] += s1
        total[2] += s2
        total[3] += s3
        total[4] += s4
    total.append(round(100.0 * total[2] / total[1], 2))
    total.append(round(100.0 * total[4] / total[3], 2))
    for i in range(1, 5):
        total[i] = to_mb(total[i])

    if not os.path.exists('report'):
        os.mkdir('report')
    with open('report/packages-%s.csv' % type, 'w+') as of:
        of.write('Package,RPM size before (MB),RPM size after (MB),Extracted size before (MB),Extracted size after (MB),RPM size ratio, Extracted ratio\n')
        of.write(','.join([str(x) for x in total]))
        of.write('\n')
        for p in sorted(package_diff, key = lambda x: x[3], reverse = True):
            of.write(','.join([str(x) for x in p]))
            of.write('\n')

    total = ['Total', '', '', 0, 0]
    file_comparison = []
    for s in sorted(todo):
        source_files[s].compare_files(type, s, target_files[s], file_comparison, total)

    total.append(round(100.0 * total[4] / total[3], 2))
    total[3] = to_mb(total[3])
    total[4] = to_mb(total[4])
    with open('report/files-%s.csv' % type, 'w+') as of:
        of.write('File,RPM,Package,Size before (MB),Size after (MB),Comparison\n')
        of.write(','.join([str(x) for x in total]))
        of.write('\n')
        for p in sorted(file_comparison, key = lambda x: x[4], reverse = True):
            of.write(','.join([str(x) for x in p]))
            of.write('\n')

print('CSV files saved to report folder')
