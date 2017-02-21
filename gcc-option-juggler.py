#!/usr/bin/env python3

import argparse
import subprocess
import random
import sys
import glob
import re
import concurrent.futures

from itertools import *
from datetime import datetime

# parser = argparse.ArgumentParser(description='')
# parser.add_argument('api_key', help = 'API key')
# parser.add_argument('--remove', nargs = '?', help = 'Remove a release from summary')
# parser.add_argument('--add', nargs = '?', help = 'Add a new release to summary, e.g. 6:7 will add 7 where 6 is included')
# parser.add_argument('--limit', nargs = '?', help = 'Limit number of bugs affected by the script')
# parser.add_argument('--doit', action = 'store_true', help = 'Really modify BUGs in the bugzilla')
# parser.add_argument('--new-target-milestone', help = 'Set a new target milestone, e.g. 4.9.3:4.9.4 will set milestone to 4.9.4 for all PRs having milestone set to 4.9.3')
# parser.add_argument('--add-known-to-fail', help = 'Set a new known to fail for all PRs affected by --new-target-milestone')
# parser.add_argument('--comment', help = 'Comment a PR for which we set a new target milestore')
# args = parser.parse_args()
#

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
                    print(m.group(1))
                    d[m.group(1)] = lines[i + 1].split(' ')

        else:
            # run without -Q
            lines = output_for_command('gcc --help=%s %s' % (name, self.level))

            for l in lines:
                parts = split_by_space(l)
                if len(parts) >= 2 and parts[1].endswith(']'):
                    key = parts[0]
                    s = parts[1]
                    s = s[s.find('=[') + 2:-1]
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

            key = parts[0]
            value = parts[1]

            if key == '-Wall' or key == 'Wextra':
                continue

            # TODO: report bug
            if key == '-m3dnowa':
                continue

            # TODO: do not disable -mno-sse because it prevents from double usage

            # TODO: report bug #3
#            if key == '-fselective-scheduling2':
#                continue

            if key == '-miamcu':
                continue

            if value == '[enabled]':
                self.options.append(BooleanFlag(key, True))
            elif value == '[disabled]':
                self.options.append(BooleanFlag(key, False))
            elif key.endswith('=') and key in enum_values:
                self.options.append(EnumFlag(key, value, enum_values[key], False))
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
        options = [random.choice(self.options).select_nondefault() for option in range(option_count)]
        source_file = random.choice(source_files)
        compiler = 'gcc' if source_file.endswith('.c') else 'g++'

        # TODO: warning
        cmd = 'timeout 10 %s -c -flto -I/home/marxin/BIG/Programming/llvm-project/libcxx/test/support/ -Wno-overflow %s %s %s' % (compiler, self.level, source_file, ' '.join(options))
        r = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        if r.returncode != 0:
            print('\n' + cmd)
            try:
                print(r.stderr.decode('utf-8'))
            except UnicodeDecodeError as e:
                print('internal compiler error: !!!cannot decode stderr!!!')
            if r.returncode == 124:
                print('internal compiler error: !!!timeout!!!')
        else:
            print('.' , end = '')
            sys.stdout.flush()

levels = [OptimizationLevel(x) for x in ['', '-O0', '-O1', '-O2', '-O3', '-Ofast', '-Os', '-Og']]
random.seed(129834719823)

def test():
    level = random.choice(levels)
    level.test(random.randint(1, 20))

with concurrent.futures.ThreadPoolExecutor(max_workers = 8) as executor:
    futures = {executor.submit(test): x for x in range(1000 * 1000)}
    for future in concurrent.futures.as_completed(futures):
        pass
