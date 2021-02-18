#!/usr/bin/env python3

import os
import sys
import re
import argparse
import datetime
import json
import subprocess
import socket
import platform

from base64 import *

script_folder = os.path.dirname(os.path.realpath(__file__))

def average(values):
    if len(values) == 0:
        return None
    elif any(map(lambda x: x == None, values)):
        return None
    else:
        return sum(values) / len(values)

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

    return None

class RsfBase:
    def __init__(self, prefix, lines):
        self.prefix = prefix
        self.lines = RsfBase.strip_lines(prefix, lines)

    @staticmethod
    def strip_lines(prefix, lines):
        stripped = []

        for line in lines:
            # print(line)
            assert line.startswith(prefix)
            stripped.append(line[len(prefix) + 1:])

        return stripped

    def get_lines(self, key, lines = None):
        if lines == None:
            lines = self.lines
        return [x for x in lines if x.startswith(key)]

    def get_values(self, key, lines = None):
        return [x.split(':')[-1].strip() for x in self.get_lines(key, lines)]

    def get_value(self, key, lines = None):
        values = self.get_values(key, lines)
        assert len(values) == 1
        return values[0]

    def get_value_or_default(self, key):
        values = self.get_values(key, lines)
        return values[0] if len(values) > 0 else None

class Benchmark(RsfBase):
    def __init__(self, name, lines, spec_folder):
        self.name = name
        self.exe_filename = self.name[self.name.find('_') + 1:]
        # exceptions that are in CPU2006
        if self.name == '482_sphinx3':
            self.exe_filename = 'sphinx_livepretend'
        elif self.name == '483_xalancbmk':
            self.exe_filename = 'Xalan'


        super(Benchmark, self).__init__('.'.join([name, 'peak']), lines)
        runs = sorted(set([x.split('.')[0] for x in self.lines]))
        self.errors = []
        self.times = []
        self.iterations = len(runs)
        self.spec_folder = os.path.abspath(spec_folder)

        for run in runs:
            lines = RsfBase.strip_lines(run, [x for x in self.lines if x.startswith(run)])
            t = self.get_value('reported_time', lines)
            self.times.append(float(t) if t != '--' else None)
            self.errors += self.get_values('error', lines)

        self.average_time = average(self.times)
        self.binary_size = None

        # parse ELF sections
        self.absolute_path = find(self.exe_filename, os.path.join(spec_folder, 'benchspec'))
        if self.absolute_path != None:
            output = subprocess.check_output([os.path.join(script_folder, 'readelf_sections.py'), self.absolute_path])
            s = output.decode('utf8')
            self.binary_size = json.loads(s)

    def to_dict(self):
        return { 'name': self.name, 'average_time': self.average_time, 'iterations': self.iterations, 'errors': ''.join(self.errors), 'absolute_path': self.absolute_path, 'binary_size': self.binary_size }

class BenchmarkGroup(RsfBase):
    def __init__(self, filename, spec_folder, spec_name):
        self.filename = filename
        lines = [x.strip() for x in open(self.filename).readlines()]
        super(BenchmarkGroup, self).__init__('spec.' + spec_name, [x for x in lines if not x.startswith('#')])

        benchmark_lines = RsfBase.strip_lines('results', self.get_lines('results'))
        benchmark_names = sorted(set([x.split('.')[0] for x in benchmark_lines]))
        self.benchmarks = [Benchmark(x, [y for y in benchmark_lines if y.startswith(x)], spec_folder) for x in benchmark_names]
        self.unitbase = self.get_value_or_default('unitbase')
        if self.unitbase == None:
            self.unitbase = self.get_value('name')

    def to_dict(self):
        return { 'group_name': self.unitbase, 'benchmarks': [x.to_dict() for x in self.benchmarks] }

class BenchmarkSuite(RsfBase):
    def __init__(self, filenames, compiler, compiler_version, flags, spec_folder, spec_name, revision, branch):
        lines = [x.strip() for x in open(filenames[0]).readlines()]
        super(BenchmarkSuite, self).__init__('spec.' + spec_name, [x for x in lines if not x.startswith('#')])
        self.time = self.get_value('time')
        self.time = datetime.datetime.fromtimestamp(int(self.time))
        self.toolset = self.get_value('toolset')
        self.suitever = self.get_value('suitever')
        self.compiler = compiler 
        self.compiler_version = compiler_version
        self.compiler_revision = revision
        self.compiler_branch = branch
        self.options = flags
        self.suitename = spec_name 

        self.groups = [BenchmarkGroup(x, spec_folder, spec_name) for x in filenames]

    def to_dict(self):
        return {
            'compiler': self.compiler,
            'compiler_version': self.compiler_version,
            'compiler_revision': self.compiler_revision,
            'compiler_branch': self.compiler_branch,
            'flags': self.options,
            'timestamp': self.time.strftime('%Y-%m-%dT%H:%M:%S'),
            'toolset': self.toolset,
            'type': self.suitename,
            'groups': [x.to_dict() for x in self.groups],
            'arch': platform.machine(),
            'hostname': socket.gethostname(),
            }

parser = argparse.ArgumentParser(description='Parse SPEC RSF file and transform selected values to JSON')
parser.add_argument('log_file', metavar = 'log_file', help = 'SPEC log output file')
parser.add_argument('compiler', metavar = 'compiler', help = 'Compiler: [gcc,llvm,icc]')
parser.add_argument('compiler_version', metavar = 'compiler_version', help = 'Compiler version')
parser.add_argument('flags', metavar = 'flags', help = 'Encoded flags in base64')
parser.add_argument('spec_folder', metavar = 'spec_folder', help = 'SPEC root folder')
parser.add_argument('spec_name', metavar = 'spec_name', help = 'SPEC name')
parser.add_argument("-o", "--output", dest="output", help = "JSON output file")
parser.add_argument("-r", "--revision", dest="revision", help = "GIT revision")
parser.add_argument("-b", "--branch", dest="branch", help = "GIT branch")

args = parser.parse_args()
args.flags = b64decode(args.flags).decode('utf-8')

lines = [x.strip() for x in open(args.log_file).readlines()]

log_file = None
key = 'The log for this run is in '
for l in lines:
    if l.startswith(key):
        log_file = l.split(key)[-1]
        break

assert log_file != None
print('Parsing SPEC log file: ' + log_file)
lines = [x.strip() for x in open(log_file).readlines()]

p = 'format: raw -> '
rsf_files = [x.split(p)[-1].strip() for x in lines if p in x]
assert len(rsf_files) > 0

suite = BenchmarkSuite(rsf_files, args.compiler, args.compiler_version, args.flags, args.spec_folder, args.spec_name, args.revision, args.branch)

if args.output == None:
    print(json.dumps(suite.to_dict(), indent = 2))
else:
    with open(args.output, 'w') as fp:
        json.dump(suite.to_dict(), fp, indent = 2)
