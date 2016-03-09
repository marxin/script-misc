#!/usr/bin/env python3

import os
import sys
import re
import argparse
import tempfile
import shutil
import time
import subprocess
import json

from tempfile import *
from collections import defaultdict
from itertools import groupby

parser = argparse.ArgumentParser(description='Display statistics about binaries.')
parser.add_argument('files', metavar = 'FILES', nargs = '+', help = 'ELF files to be compared')
parser.add_argument('--strip', dest = 'strip', action = 'store_true', help = 'strip binaries before comparison')
parser.add_argument('--compare-symbols', dest = 'compare_symbols', action = 'store_true', help = 'compare number of symbols')
parser.add_argument('--summary', dest = 'summary', action = 'store_true', help = 'summary ELF sections to: code, dynamic relocations, data, EH, rest')
parser.add_argument('--detect-optimization', dest = 'detect_optimization', action = 'store_true', help = 'detect optimizations which produced a symbol')
parser.add_argument('--format', dest = 'format', default = 'report', choices = ['report', 'csv', 'json'], help = 'output format')
parser.add_argument('--report', dest = 'report', help = 'file where results are saved')

args = parser.parse_args()

def create_temporary_copy(src):
    tf = tempfile.NamedTemporaryFile(mode='r+b', prefix='__', suffix='.tmp', delete = False)

    with open(src,'r+b') as f:
        shutil.copyfileobj(f,tf)
    
    tf.seek(0) 
    tf.close()
    return tf.name

def sizeof_fmt(num):
    for x in ['B','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.2f %s" % (num, x)
        num /= 1024.0

def to_percent(a, b):
    if b == 0:
        if a == 0:
            return '100.00 %'
        else:
            return '0.00 %'

    return str('%.2f %%' % (100.0 * a / b))

symbol_categories = [('omp', re.compile('(.*)\._omp_fn\.[0-9]+')), ('isra', re.compile('(.*)\.isra\.[0-9]+')), ('constprop', re.compile('(.*)\.constprop\.[0-9]+')), ('part', re.compile('(.*)\.part\.[0-9]+')), ('global_ctor', re.compile('_GLOBAL__sub_I_(.*)')), ('GCC_except_table', re.compile('GCC_except_table(.*)'))]

symbol_categories_demangled = [('ctor_vtable', 'construction vtable'), ('virt_thunk', 'virtual thunk'), ('non_virt_thunk', 'non-virtual thunk'), ('typeinfo', 'typeinfo name for')]

section_summary = ['code', 'dynamic_relocations', 'data', 'EH', 'rest', 'TOTAL']
section_summary_selectors = [lambda x: x == '.text',
	lambda x: x.startswith('.dyn') or x.startswith('.rela') or x.startswith('.got') or x == '.hash',
	lambda x: x.startswith('.data') or x == '.rodata',
	lambda x: x.startswith('.eh'),
	lambda x: x != 'TOTAL',
	lambda x: x == 'TOTAL']

class ElfSymbol:
    def __init__ (self, name, type, attribute):
        self.name = name
        self.demangled_name = None
        self.type = type
        self.attribute = attribute

    def __eq__(self, obj):
        return self.name == obj.name and self.type == obj.type and self.attribute == obj.attribute

    def __hash__(self):
         return hash(self.name + self.type + self.attribute)

    def __str__(self):
        return 'name: %s, type: %s, attr: %s' % (self.name, self.type, self.attribute)

    def detect_optimization(self):
        self.optimization = '(none)'
        self.canonical_name = self.name

        for r in symbol_categories:
            m = r[1].search(self.name)
            if m != None:
                self.optimization = r[0]
                self.canonical_name = m.group(1)
                return

        for r in symbol_categories_demangled:
            if self.demangled_name.startswith(r[1]):
                self.optimization = r[0]
                return

    def group(self):
        return self.type + '_' + self.attribute

class ElfSection:
    def __init__ (self, section, offset, size):
        self.section = section
        self.offset = offset
        self.size = size

class ElfContainer:
    def __init__ (self, full_path):
        self.parse_sections(full_path)

        if args.compare_symbols:
            self.parse_symbols(full_path)
            self.parse_demangled_names()

            if args.detect_optimization:
                for i, s in enumerate(self.symbols):
                    s.detect_optimization()

            sorted_input = sorted(self.symbols, key = lambda x: x.group())
            self.symbols_dictionary = {}

            for k, g in groupby(sorted_input, key = lambda x: x.group()):
                self.symbols_dictionary[k] = list(g)

    def parse_demangled_names(self):
        names = '\n'.join(map(lambda x: x.name, self.symbols))
        f = NamedTemporaryFile(delete=False)

        for n in self.symbols:
            s = n.name + '\n'
            f.write(bytes(s, 'UTF-8'))

        f.close()

        result = list([x.strip() for x in os.popen('cat %s | c++filt' % f.name).readlines()])
        os.unlink(f.name)

        for i, s in enumerate(self.symbols):
            s.demangled_name = result[i]

    def parse_sections (self, full_path):
        if args.strip:
            full_path = create_temporary_copy(full_path)            
            proc = subprocess.Popen(['strip', '-s', full_path], shell = False, stdout=subprocess.PIPE)
            proc.communicate()

        self.sections = []
        f = os.popen('readelf -S --wide ' + full_path)

        lines = f.readlines()[5:-4]

        for line in lines:
            o = line.strip()
            line = o
            line = line[line.find(']') + 1:]
            tokens = [x for x in line.split(' ') if x]
            self.sections.append(ElfSection(tokens[0], int(tokens[3], 16), int(tokens[4], 16)))

        self.total_size = os.stat(full_path).st_size
        self.sections.append(ElfSection('TOTAL', 0, self.total_size))

        if args.summary:
            old_sections = self.sections

            d = {}
            for s in section_summary:
                d[s] = 0

            for section in self.sections:
                index = next(i for i,v in enumerate(section_summary_selectors) if v(section.section))
                d[section_summary[index]] += section.size

            self.sections = []

            for k in d:
                self.sections.append(ElfSection(k, 0, d[k]))

    def parse_symbols (self, full_path):
        f = os.popen('readelf --wide -s ' + full_path)
        self.symbols = []

        for line in f.readlines():
            items = [x for x in line.strip().split(' ') if x]
            if len(items) == 8 and items[1][-1].isdigit():
                name = items[7]
                type = items[3]
                attribute = items[4]
                self.symbols.append(ElfSymbol(name, type, attribute))

    @staticmethod
    def add_to_dictionary(d, index, key, value):
        if not key in d:
            d[key] = [0, 0, 0]

        d[key][index] = value

    @staticmethod
    def get_categories(s):
        l = list(s)
        sorted_list = sorted(l, key = lambda x: x.optimization)
        return [(k, list(g)) for (k, g) in groupby(sorted_list, key = lambda x: x.optimization)]

    @staticmethod
    def compare_symbol_categories(list1, list2):
        source = set(list1)
        target = set(list2)

        same = source & target
        just_source = source - target
        just_target = target - source

        same_c = ElfContainer.get_categories(same)
        just_source_c = ElfContainer.get_categories(just_source)
        just_target_c = ElfContainer.get_categories(just_target)

        d = {}

        for i in same_c:
            ElfContainer.add_to_dictionary(d, 0, i[0], len(i[1]))

        for i in just_source_c:
            ElfContainer.add_to_dictionary(d, 1, i[0], len(i[1]))

        for i in just_target_c:
            ElfContainer.add_to_dictionary(d, 2, i[0], len(i[1]))

        for k in d.keys():
            v = d[k]
            print('%17s %12s%12s%12s%14s' % (k, v[0], v[1], v[2], to_percent(v[1], v[2])))

    def compare_symbols (self, compared):
        print('Symbol count comparison')
        print('                 category            inters.            source            target            source and target comparison')
        all_keys = set(self.symbols_dictionary.keys ()).union(set(compared.symbols_dictionary.keys()))
        fmt = '%-30s%12s%12s%14s'

        sums = [0, 0]

        for k in all_keys:
            v = []
            v2 = []

            if k in self.symbols_dictionary:
                v = self.symbols_dictionary[k]
                sums[0] = sums[0] + len(v)
            if k in compared.symbols_dictionary:
                v2 = compared.symbols_dictionary[k]
                sums[1] = sums[1] + len(v)

            print(fmt % ('=== ' + k, len(v), len(v2), to_percent(len(v2), len(v))))
            ElfContainer.compare_symbol_categories(v, v2)

        print(fmt % ('TOTAL', str(sums[0]), str(sums[1]), to_percent(sums[1], sums[0])))
        print()

        for s in self.symbols:
            print('%s:%s:%s:%s:SOURCE' % (s.type, s.attribute, s.name, s.demangled_name), file = sys.stderr)

        for s in compared.symbols:
            print('%s:%s:%s:%s:TARGET' % (s.type, s.attribute, s.name, s.demangled_name), file = sys.stderr)

    """
        lf = set(map(lambda x: x.canonical_name, self.symbols_dictionary['FUNC_LOCAL']))
        compared_lf = set(map(lambda x: x.canonical_name, compared.symbols_dictionary['FUNC_LOCAL']))

        for i in lf - compared_lf:
            print('Just in GCC: %s' % i)

        for i in compared_lf - lf:
            print('Just in CLANG: %s' % i)
    """

    def print_csv(self):
        for s in self.sections:
            print('%s:%u' % (s.section, s.size))

    def print_json(self, report_file):
        d = {}
        for s in self.sections:
            d[s.section] = s.size

        data = { 'name': 'binary_size', 'type': 'size', 'values': d}
        if report_file != None:
            with open(report_file, 'w') as f:
                f.write(json.dump(data, f, indent = 4))
        else:
            print(json.dumps(data, indent = 4))

    @staticmethod
    def print_containers (containers):
        first = containers[0]

        print('%-80s%12s%12s%12s%12s%12s' % ('section', 'portion', 'size', 'size', 'compared', 'comparison'))
        for s in sorted(first.sections, key = lambda x: x.size):
            print ('%-80s%12s%12s%12s' % (s.section, to_percent(s.size, first.total_size), sizeof_fmt(s.size), str(s.size)), end = '')

            for rest in containers[1:]:
                ss = [x for x in rest.sections if x.section == s.section]
                ss_size = 0
                if len(ss) > 0:
                    ss_size = ss[0].size

                print('%12s' % str(ss_size), end = '')
                portion = to_percent (ss_size, s.size)
                print('%12s' % portion, end = '')

            print()

containers = list(map(lambda x: ElfContainer(x), args.files))

if len(args.files) > 1:
    containers[0].compare_symbols(containers[1])

if args.format == 'report':
    ElfContainer.print_containers(containers)
elif args.format == 'csv':
    containers[0].print_csv()
elif args.format == 'json':
    containers[0].print_json(args.report)
