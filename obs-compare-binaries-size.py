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

def get_canon_name(name):
    i = name.rfind('-')
    return name[:i]

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
        self.canoname = get_canon_name(data['name'])
        self.size = data['size']
        self.extracted_size = data['extracted_size']
        self.files = dict(data['files'])
        self.canonfiles = dict((get_canon_name(x[0]), x[1]) for x in data['files'])

class Package:
    def __init__(self, data):
        self.name = data['name']
        self.sections = {}

        for k, v in data['sections'].items():
            self.sections[k] = [Rpm(x) for x in v]

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
                    cn = get_canon_name(f)
                    if cn in other_rpm.canonfiles:
                        report.append((strip_path(f), strip_path(rpm.name), strip_json(package), rpm.files[f], other_rpm.canonfiles[cn]))

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

for type in ['normal', 'devel', 'debug']:
    todo = []
    for s, s2 in source_files.items():
        if not s in target_files:
            print('Missing in LTO: ' + s)
        else:
            c = s2.compare_sections(type, target_files[s])
            if c != True:
                pass
                # print('Different RPM names: %s: %d' % (s, c))
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

