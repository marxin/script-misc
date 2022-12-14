#!/usr/bin/env python3

import argparse
import subprocess
import random
import sys
import glob
import re
import concurrent.futures
import traceback
import os
import tempfile
import logging
import shutil

from itertools import *
from threading import Lock
from datetime import datetime, timedelta
from termcolor import colored
from time import time
from os import path
from multiprocessing import Pool

known_bugs = {'clear_padding_type, at gimple-fold.c': 'PRxxx'}

script_dir = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(filename='/tmp/gcc-option-juggling.log',level=logging.DEBUG)

parser = argparse.ArgumentParser(description = 'Yet another stupid GCC fuzzer')
parser.add_argument('--iterations', type = int, default = 100, help = 'Number of tested test-cases (in thousands)')
parser.add_argument('--cflags', default = '', help = 'Additional compile flags')
parser.add_argument('--timeout', type = int, default = 10, help = 'Default timeout for GCC command')
parser.add_argument('-v', '--verbose', action = 'store_true', help = 'Verbose messages')
parser.add_argument('-l', '--logging', action = 'store_true', help = 'Log error output')
parser.add_argument('-r', '--reduce', action = 'store_true', help = 'Creduce a failing test-case')
parser.add_argument('-f', '--filter', action = 'store_true', help = 'First filter valid source files')
parser.add_argument('-m', '--maxparam', help = 'Maximum param value')
parser.add_argument('-t', '--target', default = 'x86_64', help = 'Default target', choices = ['x86_64', 'ppc64', 'ppc64le', 's390x', 'aarch64', 'arm', 'riscv64'])
args = parser.parse_args()

option_validity_cache = {}

FNULL = open(os.devnull, 'w')

empty = tempfile.NamedTemporaryFile(suffix = '.c', delete = False).name

def get_compiler_prefix():
    if args.target == 'x86_64':
        return ''
    elif args.target in ('ppc64', 'ppc64le', 's390x', 'aarch64', 'riscv64'):
        return f'{args.target}-linux-gnu-'
    elif args.target == 'arm':
        return 'arm-linux-gnueabi-'
    else:
        assert False

def is_valid_test_case_for_target(name):
    if not 'gcc.target/' in name:
        return True

    if args.target == 'x86_64':
        return 'i386' in name or 'x86_64' in name
    elif args.target == 'ppc64':
        return 'powerpc' in name
    elif args.target == 'ppc64le':
        return 'powerpc' in name
    elif args.target == 's390x':
        return 's390' in name
    elif args.target == 'arm':
        return 'arm' in name
    elif args.target == 'aarch64':
        return 'aarch64' in name
    elif args.target == 'riscv64':
        return 'riscv64' in name
    else:
        assert False

def get_compiler():
    return get_compiler_prefix() + 'gcc'

def get_compiler_by_extension(f):
    if f.endswith(('.c', '.rs')):
        return get_compiler()
    elif f.endswith(('.C', '.cpp', '.cc')):
        return get_compiler_prefix() + 'g++'
    elif f.endswith(('.f', '.f90')):
        return get_compiler_prefix() + 'gfortran'
    else:
        return None

ignored_tests = {'instantiate-typeof.cpp', 'multi-level-substitution.cpp', 'constructor-template.cpp', 'instantiate-typeof.cpp',
        'enum-unscoped-nonexistent.cpp', 'dr6xx.cpp', 'cxx1y-generic-lambdas-capturing.cpp', 'cxx1y-variable-templates_in_class.cpp',
        'temp_arg_nontype.cpp', 'constant-expression-cxx1y.cpp', 'cxx1z-using-declaration.cpp', 'pack-deduction.cpp', 'pr65693.c', 'const-init.cpp',
        'temp_arg_nontype_cxx1z.cpp', 'cxx1z-decomposition.cpp', 'vla-lambda-capturing.cpp', 'cxx0x-defaulted-functions.cpp', 'dllimport.cpp', 'type-traits.cpp',
        'for-range-examples.cpp', 'lambda-expressions.cpp', 'mangle-lambdas.cpp', 'cxx1y-generic-lambdas.cpp', 'macro_vaopt_expand.cpp', 'dllimport-members.cpp',
        'dllexport.cpp', 'lambda-mangle4.C', 'dllexport-members.cpp', 'arm-asm.c', 'cxx0x-cursory-default-delete.cpp',
        'pr89037.c', 'pr90139.c'}

def find_tests(base, contains):
    result = []
    for root, dirs, files in os.walk(base):
        for f in files:
            full = os.path.join(root, f)
            if contains in full:
                result.append(full)

    return result

source_files = find_tests('/home/marxin/Programming/gcc/gcc/', '/testsuite/')
source_files += find_tests('/home/marxin/Programming/llvm-project/', '/test/')
source_files += find_tests('/home/marxin/Programming/llvm-project/', '/test-suite/')
source_files = list(set(sorted(source_files)))
source_files = list(filter(lambda x: get_compiler_by_extension(x) != None and not any([i in x for i in ignored_tests]), source_files))

# remove RTL test-cases
source_files = list(filter(lambda x: not '/rtl/' in x, source_files))

# filter out different target tests
source_files = list(filter(is_valid_test_case_for_target, source_files))

ice_cache = set()
ice_locations = set()

source_files = set(source_files)

print('Found %d files.' % len(source_files))

def split_by_space(line):
    return [x for x in line.replace('\t', ' ').split(' ') if x != '']

def output_for_command(command):
    r = subprocess.run(command, shell = True, capture_output=True)
    assert r.returncode == 0
    lines = [x.strip() for x in r.stdout.decode('utf-8').split('\n')]
    lines = lines[1:]
    return lines

def check_option(level, option):
    if option in option_validity_cache:
        return option_validity_cache[option]

    cmd = f'{get_compiler()} -c -c {empty} {level} {option}'
    r = subprocess.run(cmd, shell = True, capture_output=True)
    result = r.returncode == 0
    option_validity_cache[option] = result
    return result

def find_ice(stderr):
    lines = stderr.split('\n')
    subject = None
    ice = 'internal compiler error: '
    ubsan_re = 'runtime error: '
    asan_re = 'ERROR: AddressSanitizer:'

    bt = []

    for l in lines:
        l = l.strip()
        if ice in l:
            subject = l[l.find(ice) + len(ice):]
            found_ice = True
        elif 'compare-debug' in l and 'error:' in l:
            return (l, l)
        elif ubsan_re in l:
            subject = l[l.find(ubsan_re) + len(ubsan_re):]
            return (subject, l)
        elif asan_re in l:
            subject = l[l.find(asan_re) + len(asan_re):]
            return (subject, l)
        elif 'in ' in l and ' at ' in l:
            subject = l
            found_ice = True
        elif l.startswith('0x') and subject == None:
            subject = ''
            bt.append(l)
        elif 'Please submit a full bug report' in l or l.strip() == 0:
            # unify stack addresses
            bt = ['0xdeadbeef' + x[x.find(' '):] if x.startswith('0x') else x for x in bt]

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
        self.name = '-mtune='
        self.options = {}

        self.options['x86_64'] = 'i386,i486,i586,pentium,lakemont,pentium-mmx,winchip-c6,winchip2,c3,samuel-2,c3-2,nehemiah,c7,esther,i686,pentiumpro,pentium2,pentium3,pentium3m,pentium-m,pentium4,pentium4m,prescott,nocona,core2,nehalem,corei7,westmere,sandybridge,corei7-avx,ivybridge,core-avx-i,haswell,core-avx2,broadwell,skylake,skylake-avx512,cannonlake,icelake-client,icelake-server,cascadelake,tigerlake,cooperlake,sapphirerapids,alderlake,bonnell,atom,silvermont,slm,goldmont,goldmont-plus,tremont,knl,knm,intel,geode,k6,k6-2,k6-3,athlon,athlon-tbird,athlon-4,athlon-xp,athlon-mp,x86-64,x86-64-v2,x86-64-v3,x86-64-v4,eden-x2,nano,nano-1000,nano-2000,nano-3000,nano-x2,eden-x4,nano-x4,k8,k8-sse3,opteron,opteron-sse3,athlon64,athlon64-sse3,athlon-fx,amdfam10,barcelona,bdver1,bdver2,bdver3,bdver4,znver1,znver2,znver3,btver1,btver2,generic,amd,native'.split(',')
        self.options['ppc64'] = '401,403,405,405fp,440,440fp,464,464fp,476,476fp,505,601,602,603,603e,604,604e,620,630,740,7400,7450,750,801,821,823,860,970,8540,a2,e300c2,e300c3,e500mc,e500mc64,e5500,e6500,ec603e,G3,G4,G5,titan,power3,power4,power5,power5+,power6,power6x,power7,power8,power9,powerpc,powerpc64,powerpc64le,rs64'.split(',')
        self.options['ppc64le'] = self.options['ppc64']
        self.options['aarch64'] = 'generic,cortex-a35,cortex-a53,cortex-a57,cortex-a72,exynos-m1,qdf24xx,thunderx,xgene1'.split(',')
        self.options['s390x'] = 'z900,z990,z9-109,z9-ec,z10,z196,zEC12,z13'.split(',')
        self.options['arm'] = 'arm2,arm250,arm3,arm6,arm60,arm600,arm610,arm620,arm7,arm7m,arm7d,arm7dm,arm7di,arm7dmi,arm70,arm700,arm700i,arm710,arm710c,arm7100,arm720,arm7500,arm7500fe,arm7tdmi,arm7tdmi-s,arm710t,arm720t,arm740t,strongarm,strongarm110,strongarm1100,strongarm1110,arm8,arm810,arm9,arm9e,arm920,arm920t,arm922t,arm946e-s,arm966e-s,arm968e-s,arm926ej-s,arm940t,arm9tdmi,arm10tdmi,arm1020t,arm1026ej-s,arm10e,arm1020e,arm1022e,arm1136j-s,arm1136jf-s,mpcore,mpcorenovfp,arm1156t2-s,arm1156t2f-s,arm1176jz-s,arm1176jzf-s,generic-armv7-a,cortex-a5,cortex-a7,cortex-a8,cortex-a9,cortex-a12,cortex-a15,cortex-a17,cortex-a32,cortex-a35,cortex-a53,cortex-a57,cortex-a72,cortex-r4,cortex-r4f,cortex-r5,cortex-r7,cortex-r8,cortex-m7,cortex-m4,cortex-m3,cortex-m1,cortex-m0,cortex-m0plus,cortex-m1.small-multiply,cortex-m0.small-multiply,cortex-m0plus.small-multiply,exynos-m1,qdf24xx,marvell-pj4,xscale,iwmmxt,iwmmxt2,ep9312,fa526,fa626,fa606te,fa626te,fmp626,fa726te,xgene1'.split(',')
        self.options['riscv64'] = 'rv64i'.split(',')

        self.tuples = []
        self.ignore_m32 = False

    def build(self, value):
        f = None
        if args.target == 'riscv64':
            return '-march=%s -mabi=lp64' % value

        if args.target == 'arm' or args.target == 'aarch64' or args.target == 'ppc64' or args.target == 'ppc64le':
            f = '-mtune=%s -mcpu=%s'
        else:
            f = '-mtune=%s -march=%s'
        return f % (value, value)

    def check_option(self, level):
        for o in self.options[args.target]:
            s = self.build(o)
            r = check_option(level, s)
            needs_m32 = False
            if not r:
                r = check_option(level, s + ' -m32')
                if not r:
                    continue
                needs_m32 = True

            if not needs_m32 or not self.ignore_m32:
                self.tuples.append((o, needs_m32))

        return True

    def select_nondefault(self):
        choice = random.choice(self.tuples)
        s = self.build(choice[0])
        if choice[1]:
            s += ' -m32'

        return s

class IntegerRangeFlag:
    def __init__(self, name, min, max):
        self.name = name
        self.min = min
        self.max = max

    def check_option(self, level):
        r = [self.min, self.max] if self.max > 100 else range(self.min, self.max)

        for o in r:
            s = self.name + str(o)
            r = check_option(level, s)
            if r == False:
                return False

        return True

    def select_nondefault(self):
        choice = random.randint(self.min, self.max)

        s = self.name + str(choice)
        return s

class Param:
    def __init__(self, name, default):
        self.name = name
        self.default = int(default)

        m = re.match(r'(?P<name>.*)=<(?P<min>[0-9]+),(?P<max>[0-9]+)>', name)
        if m != None:
            self.name = m.group('name')
            self.min = int(m.group('min'))
            self.max = int(m.group('max'))
        else:
            self.name = self.name.rstrip('=')
            self.min = 0
            self.max = 0

        if self.default == -1:
            self.default = 0

        if self.min == -1:
            self.min = 0

        if self.max == 0:
            self.max = 2147483647

        limitted_params = {'max-iterations-to-track', 'min-nondebug-insn-uid', 'max-completely-peel-times', 'max-completely-peeled-insns',
            'jump-table-max-growth-ratio-for-size', 'jump-table-max-growth-ratio-for-speed'}

        for l in limitted_params:
            if l in self.name:
                self.max = 1000
                break

        if args.maxparam != None:
            self.max = int(args.maxparam)

    def check_option(self, level):
        return check_option(level, '%s=%d' % (self.name, self.default))

    def select_nondefault(self):
        value = None
        coin = random.randint(0, 2)
        if coin == 0:
            value = self.min
        elif coin == 1:
            value = self.max
        else:
            value = random.randint(self.min, self.max)

        return '%s=%d' % (self.name, value)

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
        print('Options for %s: %d' % (self.level, len(self.options)))

    def print_options(self):
        for o in self.options:
            print(str(o) + ': option: ' + o.name)

    def parse_enum_values(self, name):
        d = {}

        if name == 'target':
            # enums are listed at the end
            lines = output_for_command(f'{get_compiler()} -c -Q --help={name} {self.level}')
            start = takewhile(lambda x: x != '', lines)
            lines = lines[len(list(start)):]

            for i, v in enumerate(lines):
                m = re.match('.* (-m.*=).*', v)
                if m != None:
                    v = m.group(1)
                    # handle: -mindirect-branch=/-mfunction-return=
                    if '/' in v:
                        for p in v.split('/'):
                            d[p] = lines[i + 1].split(' ')
                    else:
                        d[v] = lines[i + 1].split(' ')

        else:
            # run without -Q
            lines = output_for_command(f'{get_compiler()} -c --help={name} {self.level}')

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

        for l in output_for_command(f'{get_compiler()} -c -Q --help={name} {self.level}'):
            if l == '':
               break
            parts = split_by_space(l)

            if len(parts) != 2:
                # TODO
                continue
            elif '--param=' in l:
                continue

            original = parts[0]
            i = parts[0].find('=')
            if i != -1 and parts[1] != '[enabled]' and parts[1] != '[disabled]':
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
                    assert original.endswith('<number>') or original.endswith('<byte-size>')

                self.options.append(IntegerRangeFlag(key, min, max))
            else:
                print('Parsing error of option: ' + l)
                # TODO
                pass

    def parse_params(self):
        for l in output_for_command(f'{get_compiler()} -c -Q --help=params {self.level}'):
            if l == '':
                continue
            elif 'available in' in l:
                continue
            parts = split_by_space(l)

            assert len(parts) == 2
            if parts[1][0].isdigit():
                self.options.append(Param(parts[0], parts[1]))

    def add_interesting_options(self):
        sanitize_values = 'address,kernel-address,thread,leak,undefined,vptr,shift,integer-divide-by-zero,unreachable,vla-bound,null,return,signed-integer-overflow,bounds,bounds-strict,alignment,object-size,float-divide-by-zero,float-cast-overflow,nonnull-attribute,returns-nonnull-attribute,bool,enum'.split(',')
        if args.target != 'riscv64':
            self.options.append(EnumFlag('-fsanitize=', None, sanitize_values, False))

    def filter_options(self, l):
        filtered = []
        skipped_options = {'-fselective-scheduling', '-fselective-scheduling2', '-mlra', '-fsave-optimization-record',
                '-Werror', '-fmodulo-sched', '--param=destructive-interference-size', '--param=constructive-interference-size',
                '-gstatement-frontiers'}

        if args.target == 'x86_64':
            skipped_options.add('-mforce-indirect-call')
            skipped_options.add('-mandroid')
            skipped_options.add('-mabi=')
        elif args.target == 'ppc64' or args.target == 'ppc64le':
            skipped_options.add('-m32')
            skipped_options.add('-mavoid-indexed-addresses')
            skipped_options.add('-mpopcntd')
            skipped_options.add('-maltivec')
            skipped_options.add('-mfprnd')
            skipped_options.add('-mno-power8-vector')
            skipped_options.add('-mrop-protect')
        elif args.target == 'aarch64':
            skipped_options.add('-mabi')
            skipped_options.add('-ftrivial-auto-var-init')


        if args.target != 'x86_64':
            skipped_options.add('-freorder-blocks-and-partition')

        for option in self.options:
            if option.name in skipped_options:
                continue

            # skip all -march option values that need -m32
            if args.target == 'ppc64' or args.target == 'ppc64le':
                if type(option) is MarchFlag:
                    option.ignore_m32 = True

            r = option.check_option(self.level)
            if r:
                filtered.append(option)

        return filtered

    def test(self, option_count):
        options = [random.choice(self.options) for option in range(option_count)]
        source_file = random.sample(list(source_files), 1)[0]
        compiler = get_compiler_by_extension(source_file)
        options = [o.select_nondefault() for o in options]

        # TODO: warning
        cmd = 'timeout %d %s %s -fmax-errors=1 -I/home/marxin/Programming/llvm-project/libcxx/test/support/ -Wno-overflow %s %s %s -o/dev/null -S' % (args.timeout, compiler, args.cflags, self.level, source_file, ' '.join(options))
        my_env = os.environ.copy()
        my_env['UBSAN_OPTIONS'] = 'color=never halt_on_error=1'
        my_env['ASAN_OPTIONS'] = 'color=never detect_leaks=0'
        my_env['GCCRS_INCOMPLETE_AND_EXPERIMENTAL_COMPILER_DO_NOT_USE'] = '1'

        r = subprocess.run(cmd, shell = True, capture_output=True, env = my_env)
        if r.returncode != 0:
            try:
                stderr = r.stderr.decode('utf-8')
                ice = find_ice(stderr)
                # TODO: remove
                if ice != None and not ice[1] in ice_cache and not any([x in ice[0] for x in known_bugs.keys()]):
                    ice_locations.add(ice[0])
                    ice_cache.add(ice[1])
                    print(colored('warning: NEW ICE #%d: %s' % (len(ice_cache), ice[0]), 'red'))
                    print(cmd)
                    print(ice[1])
                    print()
                    self.reduce(cmd)
                    sys.stdout.flush()
                elif args.logging:
                    logging.debug(cmd)
                    logging.debug(stderr)
            except UnicodeDecodeError as e:
                pass
            if r.returncode == 124 and args.verbose:
                print(colored('TIMEOUT:', 'red'))
                print(cmd)

    def reduce(self, cmd):
        r = subprocess.run(os.path.join(script_dir, "gcc-reduce-flags.py") + " '" + cmd + "'", shell = True, capture_output=True)
        assert r.returncode == 0
        reduced_command = r.stdout.decode('utf-8').strip()
        print(colored('Reduced command: ' + reduced_command, 'green'))

        if args.reduce:
            self.reduce_testcase(reduced_command)

    def reduce_testcase(self, cmd):
        parts = cmd.split(' ')
        f = parts[1]
        compiler = get_compiler_by_extension(f)
        assert compiler != None

        if not compiler.endswith('gcc') and not compiler.endswith('g++'):
            return

        suffix = '.i' if compiler.endswith('gcc') else '.ii'

        r = subprocess.run(cmd + ' -E', shell = True, capture_output=True)
        assert r.returncode == 0
        content = r.stdout.decode('utf-8')

        extension = path.splitext(f)[1]
        source = tempfile.NamedTemporaryFile(mode = 'w+', suffix = suffix, delete = False)
        source.write(content)
        source.close()
        source_filename = path.basename(source.name)

        # generate reduce-ice shell script
        reduce_script = tempfile.NamedTemporaryFile(mode = 'w+', suffix = '.sh', delete = False)

        tmp = """
#!/bin/sh

TC1=${1:-%s}
COMMAND="%s $TC1 -c"

$COMMAND 2>&1 | grep 'internal compiler'

if ! test $? = 0; then
  exit 1
fi

exit 0"""
        c = ' '.join([parts[0]] + parts[2:])
        reduce_script.write(tmp % (source_filename, c))
        reduce_script.close()
        os.chmod(reduce_script.name, 0o766)

        start = time()
        try:
            r = subprocess.run(f'creduce --n 10 {reduce_script.name} {source_filename}', shell = True, stdout = subprocess.PIPE, timeout = 500)
            assert r.returncode == 0
            lines = r.stdout.decode('utf-8').split('\n')
            lines = list(dropwhile(lambda x: not '*******' in x, lines))
            print('\n'.join(lines))
            print(colored('CREDUCE ', 'cyan'), end = '')
            print(f'took {str(time() - start)} s, to test:\n{c} {source.name}')
        except TimeoutExpired as e:
            print('CREDUCE timed out!')

os.chdir('/tmp/')
levels = [OptimizationLevel(x) for x in ['', '-O0', '-O1', '-O2', '-O3', '-Ofast', '-Os', '-Oz', '-Og']]

threads = 32
counter = 1000 * args.iterations
lock = Lock()

def test(i):
    level = random.choice(levels)
    level.test(200)

filtered_source_files = set()

def filter_source_files():
    while True:
        global source_files
        global filtered_source_files
        source = None
        with lock:
            if not source_files:
                return
            source = source_files.pop()

        compiler = get_compiler_by_extension(source)
        cmd = 'timeout %d %s %s -fmax-errors=1 -I/home/marxin/Programming/llvm-project/libcxx/test/support/ -Wno-overflow %s -o/dev/null -S' % (args.timeout, args.cflags, compiler, source)
        r = subprocess.run(cmd, shell = True, capture_output=True)
        if r.returncode == 0:
            filtered_source_files.add(source)

if args.filter:
    start = time()
    with concurrent.futures.ThreadPoolExecutor(max_workers = threads) as executor:
        futures = {executor.submit(filter_source_files): x for x in range(threads)}
        for future in concurrent.futures.as_completed(futures):
            data = future.result()
            pass

    print('Filtering took: %s' % str(time() - start))
    source_files = filtered_source_files
    print('Filtered source files: %d.' % len(source_files))

with Pool(threads) as p:
    p.map(test, range(counter))

print('=== SUMMARY ===')
for i in ice_locations:
    print('ICE: %s' % i)
