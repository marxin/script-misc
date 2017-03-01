#!/usr/bin/env python3

import argparse
import subprocess
import random
import sys
import glob
import re
import concurrent.futures
import traceback

from itertools import *
from datetime import datetime
from termcolor import colored
from time import time

parser = argparse.ArgumentParser(description = 'Yet another stupid GCC fuzzer')
parser.add_argument('--iterations', type = int, default = 100, help = 'Number of tested test-cases (in thousands)')
parser.add_argument('--cflags', help = 'Additional compile flags')
parser.add_argument('--timeout', type = int, default = 10, help = 'Default timeout for GCC command')
parser.add_argument('-v', '--verbose', action = 'store_true', help = 'Verbose messages')
args = parser.parse_args()

option_validity_cache = {}

def get_compiler_by_extension(f):
    if f.endswith('.c'):
        return 'gcc'
    elif f.endswith('.C') or f.endswith('.cpp'):
        return 'g++'
    else:
        return None

source_files = glob.glob('/home/marxin/Programming/gcc/gcc/testsuite/**/*', recursive = True)
source_files += glob.glob('/home/marxin/BIG/Programming/llvm-project/**/test/**/*', recursive = True)
source_files = list(filter(lambda x: get_compiler_by_extension(x) != None, source_files))

ice_cache = set()

for f in source_files:
    get_compiler_by_extension(f)

print('Found %d files.' % len(source_files))

def split_by_space(line):
    return [x for x in line.replace('\t', ' ').split(' ') if x != '']

def output_for_command(command):
    r = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    assert r.returncode == 0
    lines = [x.strip() for x in r.stdout.decode('utf-8').split('\n')]
    lines = lines[1:]
    return lines

def check_option(level, option):
    if option in option_validity_cache:
        return option_validity_cache[option]

    cmd = 'gcc -c /tmp/empty.c %s %s' % (level, option)
    r = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    result = r.returncode == 0
    if not result:
        print(cmd)
    option_validity_cache[option] = result
    return result

def find_ice(stderr):
    lines = stderr.split('\n')
    subject = None
    ice = 'internal compiler error: '

    bt = []

    for l in lines:
        l = l.strip()
        if ice in l:
            subject = l[l.find(ice) + len(ice):]
            found_ice = True
        elif l.startswith('0x') and subject == None:
            subject = ''
            bt.append(l)
        elif 'Please submit a full bug report' in l:
            return (subject, '\n'.join(bt))
        elif subject != None:
            bt.append(l)

    return None

class BooleanFlag:
    def __init__(self, name, default):
        self.name = name
        self.default = default

    def check_option(self, level):
        return check_option(level, self.switch_option())

    def switch_option(self):
        assert self.name.startswith('-f') or self.name.startswith('-m') or self.name.startswith('-W')
        prefix = self.name[:2]
        option = self.name[2:]
        if option.startswith('no-'):
            return prefix + option[3:]
        else:
            return prefix + 'no-' + option

    def select_nondefault(self):
        return self.switch_option() if self.default else self.name

class EnumFlag:
    def __init__(self, name, default, values, multi):
        self.name = name
        self.default = default
        self.values = values
        self.multi = multi

    def check_option(self, level):
        for value in self.values:
            if not check_option(level, self.name + value):
                return False

        return True

    def select_nondefault(self):
        options = [x for x in self.values if x != self.default]
        choice = None
        if self.multi:
            choice = ','.join(random.sample(self.values, random.randint(1, len(self.values))))
        else:
            choice = random.choice(options)

        return self.name + choice

class MarchFlag:
    def __init__(self):
        self.name = '-march='
        self.options = 'native,i386,i486,i586,pentium,lakemont,pentium-mmx,pentiumpro,i686,pentium2,pentium3,pentium3m,pentium-m,pentium4,pentium4m,prescott,nocona,core2,nehalem,westmere,sandybridge,ivybridge,haswell,broadwell,skylake,bonnell,silvermont,knl,skylake-avx512,k6,k6-2,k6-3,athlon,athlon-tbird,athlon-4,athlon-xp,athlon-mp,k8,opteron,athlon64,athlon-fx,k8-sse3,opteron-sse3,athlon64-sse3,amdfam10,barcelona,bdver1,bdver2,bdver3,bdver4,znver1,btver1,btver2,winchip-c6,winchip2,c3,c3-2,geode'.split(',')
        self.tuples = []

    def check_option(self, level):
        for o in self.options:
            s = self.name + o
            r = check_option(level, s)
            needs_m32 = False
            if not r:
                r = check_option(level, s + ' -m32')
                assert r
                needs_m32 = True

            self.tuples.append((o, needs_m32))

        return True

    def select_nondefault(self):
        choice = random.choice(self.tuples)
        s = self.name + choice[0]
        if choice[1]:
            s += ' -m32'

        return s

class IntegerRangeFlag:
    def __init__(self, name, min, max):
        self.name = name
        self.min = min
        self.max = max

    def check_option(self, level):
        r = [self.min, self.max] if self.max > 100 else range(self.min, self.max + 1)

        for o in r:
            s = self.name + str(o)
            r = check_option(level, s)
            if r == False:
                return False

        return True

    def select_nondefault(self):
        choice = random.randint(self.min, self.max + 1)

        s = self.name + str(choice)
        return s

class Param:
    def __init__(self, name, tokens):
        self.name = name
        self.default = int(tokens[1])
        self.min = int(tokens[3])
        self.max = int(tokens[5])

        if self.default == -1:
            self.default = 0

        if self.min == -1:
            self.min = 0

        if self.max == 0:
            self.max = 2147483647

        # TODO: write somewhere these
        if self.name == 'max-iterations-to-track':
            self.max = 1000

    def check_option(self, level):
        return check_option(level, '--param %s=%d' % (self.name, self.default))

    def select_nondefault(self):
        value = None
        coin = random.randint(0, 2)
        if coin == 0:
            value = self.min
        elif coin == 1:
            value = self.max
        else:
            value = random.randint(self.min, self.max)

        return '--param %s=%d' % (self.name, value)

class OptimizationLevel:
    def __init__(self, level):
        self.level = level
        self.options = []

        self.options.append(MarchFlag())
        self.parse_options('target')
        self.parse_options('optimize')
        self.parse_options('warning')
        self.parse_params()
        self.add_interesting_options()

        self.options = self.filter_options(self.options)

    def parse_enum_values(self, name):
        d = {}

        if name == 'target':
            # enums are listed at the end
            lines = output_for_command('gcc -Q --help=%s %s' % (name, self.level))
            start = takewhile(lambda x: x != '', lines)
            lines = lines[len(list(start)):]

            for i, v in enumerate(lines):
                m = re.match('.* (-m.*=).*', v)
                if m != None:
                    d[m.group(1)] = lines[i + 1].split(' ')

        else:
            # run without -Q
            lines = output_for_command('gcc --help=%s %s' % (name, self.level))

            for l in lines:
                parts = split_by_space(l)

                if len(parts) >= 2 and parts[0].endswith(']') and '=' in parts[0]:
                    parts2 = parts[0].split('=')
                    key = parts2[0] + '='
                    s = parts2[1][1:-1]
                    d[key] = s.split('|')


        return d

    def parse_options(self, name):
        enum_values = self.parse_enum_values(name)

        for l in output_for_command('gcc -Q --help=%s %s' % (name, self.level)):
            if l == '':
               break
            parts = split_by_space(l)

            if len(parts) != 2:
                # TODO
                continue

            original = parts[0]
            i = parts[0].find('=')
            if i != -1:
                parts[0] = parts[0][:i+1]

            key = parts[0]
            value = parts[1]

            if key == '-Wall' or key == 'Wextra':
                continue

            if key == '-miamcu' or key == '-march=' or key == '-mtune=':
                continue

            if value == '[enabled]':
                self.options.append(BooleanFlag(key, True))
            elif value == '[disabled]':
                self.options.append(BooleanFlag(key, False))
            elif key.endswith('=') and key in enum_values:
                self.options.append(EnumFlag(key, value, enum_values[key], False))
            elif original[-1] == '>' and '=' in original:
                i = original.find('=')
                value = original[i+2:-1]
                key = original[:i+1]

                min = 1
                max = 4294967294

                parts = value.split(',')
                if len(parts) == 2:
                    min = int(parts[0])
                    max = int(parts[1])
                else:
                    assert original.endswith('<number>')

                self.options.append(IntegerRangeFlag(key, min, max))
            else:
                print('WARNING: parsing error: ' + l)
                # TODO
                pass

    def parse_params(self):
        for l in output_for_command('gcc -Q --help=params %s' % (self.level)):
            if l == '':
                continue
            parts = split_by_space(l)

            assert len(parts) == 7
            self.options.append(Param(parts[0], parts[1:]))

    def add_interesting_options(self):
        sanitize_values = 'address,kernel-address,thread,leak,undefined,vptr'.split(',')
        self.options.append(EnumFlag('-fsanitize=', None, sanitize_values, False))

    def filter_options(self, l):
        filtered = []

        for option in self.options:
            r = option.check_option(self.level)
            if not r:
                print('failed: ' + option.name)
            else:
                filtered.append(option)

        return filtered

    def test(self, option_count):
        try:
            options = [random.choice(self.options).select_nondefault() for option in range(option_count)]
            source_file = random.choice(source_files)
            compiler = 'gcc' if source_file.endswith('.c') else 'g++'

            # TODO: warning
            cmd = 'timeout %d %s -c %s -I/home/marxin/BIG/Programming/llvm-project/libcxx/test/support/ -Wno-overflow %s %s %s -o/dev/null' % (args.timeout, compiler, args.cflags, self.level, source_file, ' '.join(options))
            r = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            if r.returncode != 0:
                try:
                    stderr = r.stderr.decode('utf-8')
                    ice = find_ice(stderr)
                    if ice != None and not ice[1] in ice_cache:
                        ice_cache.add(ice[1])
                        print(colored('NEW ICE #%d: %s' % (len(ice_cache), ice[0]), 'red'))
                        print(cmd)
                        print(ice[1])
                        print()
                except UnicodeDecodeError as e:
                    print('internal compiler error: !!!cannot decode stderr!!!')
                if r.returncode == 124:
                    print(colored('TIMEOUT:', 'red'))
                    print(cmd)
        except Exception as e:
            print('FATAL ERROR')
            traceback.print_exc(file = sys.stdout)

levels = [OptimizationLevel(x) for x in ['', '-O0', '-O1', '-O2', '-O3', '-Ofast', '-Os', '-Og']]
random.seed(2345234523)

def test():
    level = random.choice(levels)
    level.test(random.randint(1, 20))

start = time()
N = 1000

with concurrent.futures.ThreadPoolExecutor(max_workers = 8) as executor:
    for i in range(1, args.iterations):
        futures = {executor.submit(test): x for x in range(N)}
        for future in concurrent.futures.as_completed(futures):
            pass
        if args.verbose:
            c = i * N
            print('progress: %d/%d, %.2f tests/s' % (c, args.iterations * N, c / (time() - start)))
