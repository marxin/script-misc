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

from itertools import *
from datetime import datetime, timedelta
from termcolor import colored
from time import time
from os import path
import tempfile
import logging
import shutil

known_bugs = {
        'in lambda_expr_this_capture, at cp/lambda.c:720': 'PR79651',
        'in assemble_integer, at varasm.c:2754': 'PR80163',
        'in print_reg, at config/i386/i386.c:': 'invalid target',
        'in lookup_base, at cp/search.c:203': 'PR71450',
        'int_mode_for_mode, at stor-layout.c:406': 'PR79733',
        'print.c:681': 'PR79886',
        'expected record_type or union_type or qual_union_type, have template_type_parm in lookup_base, at cp/search.c': 'PR71450',
        'in ira_init_register_move_cost, at ira.c:1580': 'different target probably',
        'in make_decl_rtl, at varasm.c:1311': 'PR80168',
        'in arm_print_operand, at config/arm/arm.c': 'ARM wrong target assembly',
        'in insert_vi_for_tree, at tree-ssa-structalias.c:2807': 'PR79766',
        'in print_operand, at config/rs6000/rs6000.c': 'PPC invalid assembly',
        'canonical types differ for identical types __vector(4) int and V4i {aka __vector(4) int}': 'PR79905',
        'in s390_compare_and_branch_condition_mask, at config/s390/s390.c': 's390x strange assembly from a different target',
        'in linemap_macro_map_lookup, at libcpp/line-map.c': 'invalid C++ code',
        'in lazily_declare_fn, at cp/method.c': 'invalid code',
        'in tsubst_pack_expansion, at cp/pt.c': 'invalid C++ code',
        'in pop_local_binding, at cp/name-lookup.c': 'invalid C++ code',
        'ix86_expand_prologue, at config/i386/i386.c': 'PR80969',
        'output_operand: invalid use of register': 'invalid target',
        'in df_compact_blocks, at df-core.c': 'PR81126'
        }

script_dir = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(filename='/tmp/gcc-option-juggling.log',level=logging.DEBUG)

parser = argparse.ArgumentParser(description = 'Yet another stupid GCC fuzzer')
parser.add_argument('--iterations', type = int, default = 100, help = 'Number of tested test-cases (in thousands)')
parser.add_argument('--cflags', default = '', help = 'Additional compile flags')
parser.add_argument('--timeout', type = int, default = 10, help = 'Default timeout for GCC command')
parser.add_argument('-v', '--verbose', action = 'store_true', help = 'Verbose messages')
parser.add_argument('-l', '--logging', action = 'store_true', help = 'Log error output')
parser.add_argument('-c', '--csmith', action = 'store_true', help = 'Utilize csmith random tests')
parser.add_argument('-t', '--target', default = 'x86_64', help = 'Default target', choices = ['x86_64', 'ppc64', 'ppc64le', 's390x', 'aarch64', 'arm'])
args = parser.parse_args()

option_validity_cache = {}
failed_tests = 0


empty = tempfile.NamedTemporaryFile(suffix = '.c', delete = False).name

def get_compiler_prefix():
    if args.target == 'x86_64':
        return ''
    elif args.target == 'ppc64':
        return 'ppc64-linux-gnu-'
    elif args.target == 'ppc64le':
        return 'ppc64le-linux-gnu-'
    elif args.target == 's390x':
        return 's390x-linux-gnu-'
    elif args.target == 'arm':
        return 'arm-linux-gnueabi-'
    elif args.target == 'aarch64':
        return 'aarch64-linux-gnu-'
    else:
        assert False

def get_compiler():
    return get_compiler_prefix() + 'gcc'

def get_compiler_by_extension(f):
    if f.endswith('.c'):
        return get_compiler()
    elif f.endswith('.C') or f.endswith('.cpp'):
        return get_compiler_prefix() + 'g++'
    elif f.endswith('.f') or f.endswith('.f90'):
        return get_compiler_prefix() + 'gfortran'
    else:
        return None

ignored_tests = set(['instantiate-typeof.cpp', 'multi-level-substitution.cpp', 'constructor-template.cpp', 'instantiate-typeof.cpp',
        'enum-unscoped-nonexistent.cpp', 'dr6xx.cpp', 'cxx1y-generic-lambdas-capturing.cpp', 'cxx1y-variable-templates_in_class.cpp',
        'temp_arg_nontype.cpp', 'constant-expression-cxx1y.cpp', 'cxx1z-using-declaration.cpp', 'pack-deduction.cpp', 'pr65693.c', 'const-init.cpp',
        'temp_arg_nontype_cxx1z.cpp', 'cxx1z-decomposition.cpp', 'vla-lambda-capturing.cpp'])

source_files = glob.glob('/home/marxin/Programming/gcc/gcc/testsuite/**/*', recursive = True)
source_files += glob.glob('/home/marxin/BIG/Programming/llvm-project/**/test/**/*', recursive = True)
source_files = list(filter(lambda x: get_compiler_by_extension(x) != None and not any([i in x for i in ignored_tests]), source_files))

# Prepare csmith tests
if args.csmith:
    cdir = '/tmp/csmith-tmp'
    if os.path.exists(cdir):
        shutil.rmtree(cdir)
    os.mkdir(cdir)
    n = 200
    print('Using temporary cdir: %s, generating 2x%d tests' % (cdir, n))
    for i in range(n):
        f = tempfile.NamedTemporaryFile(mode = 'w+', dir = cdir, suffix = '.cpp', delete = False)
        subprocess.check_output('csmith --lang-cpp -o %s' % f.name, shell = True)
        print('.', end = '')
        sys.stdout.flush()

    for i in range(n):
        f = tempfile.NamedTemporaryFile(mode = 'w+', dir = cdir, suffix = '.c', delete = False)
        subprocess.check_output('csmith -o %s' % f.name, shell = True)
        print('.', end = '')
        sys.stdout.flush()

    print()

    source_files = glob.glob('%s/*' % cdir, recursive = True)
    args.cflags += ' -Wno-narrowing'

# remove RTL test-cases
source_files = list(filter(lambda x: not '/rtl/' in x, source_files))

ice_cache = set()
ice_locations = set()

for f in source_files:
    get_compiler_by_extension(f)

print('Found %d files.' % len(source_files))

def split_by_space(line):
    return [x for x in line.replace('\t', ' ').split(' ') if x != '']

def output_for_command(command):
    print(command)
    r = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    assert r.returncode == 0
    lines = [x.strip() for x in r.stdout.decode('utf-8').split('\n')]
    lines = lines[1:]
    return lines

def check_option(level, option):
    if option in option_validity_cache:
        return option_validity_cache[option]

    cmd = '%s -c %s %s %s' % (get_compiler(), empty, level, option)
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
        elif 'in ' in l and ' at ' in l:
            subject = l
            found_ice = True
        elif l.startswith('0x') and subject == None:
            subject = ''
            bt.append(l)
        elif 'Please submit a full bug report' in l:
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

        self.options['x86_64'] = 'native,i386,i486,i586,pentium,lakemont,pentium-mmx,pentiumpro,i686,pentium2,pentium3,pentium3m,pentium-m,pentium4,pentium4m,prescott,nocona,core2,nehalem,westmere,sandybridge,ivybridge,haswell,broadwell,skylake,bonnell,silvermont,knl,skylake-avx512,k6,k6-2,k6-3,athlon,athlon-tbird,athlon-4,athlon-xp,athlon-mp,k8,opteron,athlon64,athlon-fx,k8-sse3,opteron-sse3,athlon64-sse3,amdfam10,barcelona,bdver1,bdver2,bdver3,bdver4,znver1,btver1,btver2,winchip-c6,winchip2,c3,c3-2,geode'.split(',')
        self.options['ppc64'] = '401,403,405,405fp,440,440fp,464,464fp,476,476fp,505,601,602,603,603e,604,604e,620,630,740,7400,7450,750,801,821,823,860,970,8540,a2,e300c2,e300c3,e500mc,e500mc64,e5500,e6500,ec603e,G3,G4,G5,titan,power3,power4,power5,power5+,power6,power6x,power7,power8,power9,powerpc,powerpc64,powerpc64le,rs64'.split(',')
        self.options['ppc64le'] = self.options['ppc64']
        self.options['aarch64'] = 'generic,cortex-a35,cortex-a53,cortex-a57,cortex-a72,exynos-m1,qdf24xx,thunderx,xgene1'.split(',')
        self.options['s390x'] = 'z900,z990,z9-109,z9-ec,z10,z196,zEC12,z13'.split(',')
        self.options['arm'] = 'arm2,arm250,arm3,arm6,arm60,arm600,arm610,arm620,arm7,arm7m,arm7d,arm7dm,arm7di,arm7dmi,arm70,arm700,arm700i,arm710,arm710c,arm7100,arm720,arm7500,arm7500fe,arm7tdmi,arm7tdmi-s,arm710t,arm720t,arm740t,strongarm,strongarm110,strongarm1100,strongarm1110,arm8,arm810,arm9,arm9e,arm920,arm920t,arm922t,arm946e-s,arm966e-s,arm968e-s,arm926ej-s,arm940t,arm9tdmi,arm10tdmi,arm1020t,arm1026ej-s,arm10e,arm1020e,arm1022e,arm1136j-s,arm1136jf-s,mpcore,mpcorenovfp,arm1156t2-s,arm1156t2f-s,arm1176jz-s,arm1176jzf-s,generic-armv7-a,cortex-a5,cortex-a7,cortex-a8,cortex-a9,cortex-a12,cortex-a15,cortex-a17,cortex-a32,cortex-a35,cortex-a53,cortex-a57,cortex-a72,cortex-r4,cortex-r4f,cortex-r5,cortex-r7,cortex-r8,cortex-m7,cortex-m4,cortex-m3,cortex-m1,cortex-m0,cortex-m0plus,cortex-m1.small-multiply,cortex-m0.small-multiply,cortex-m0plus.small-multiply,exynos-m1,qdf24xx,marvell-pj4,xscale,iwmmxt,iwmmxt2,ep9312,fa526,fa626,fa606te,fa626te,fmp626,fa726te,xgene1'.split(',')

        self.tuples = []

    def build(self, value):
        f = None
        if  args.target == 'arm' or args.target == 'aarch64' or args.target == 'ppc64' or args.target == 'ppc64le':
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

        # TODO: likewise
        if self.name == 'min-nondebug-insn-uid':
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

        # self.print_options()

        self.options = self.filter_options(self.options)

    def print_options(self):
        for o in self.options:
            print(str(o) + ': option: ' + o.name)

    def parse_enum_values(self, name):
        d = {}

        if name == 'target':
            # enums are listed at the end
            lines = output_for_command('%s -Q --help=%s %s' % (get_compiler(), name, self.level))
            start = takewhile(lambda x: x != '', lines)
            lines = lines[len(list(start)):]

            for i, v in enumerate(lines):
                m = re.match('.* (-m.*=).*', v)
                if m != None:
                    d[m.group(1)] = lines[i + 1].split(' ')

        else:
            # run without -Q
            lines = output_for_command('%s --help=%s %s' % (get_compiler(), name, self.level))

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

        for l in output_for_command('%s -Q --help=%s %s' % (get_compiler(), name, self.level)):
            if l == '':
               break
            parts = split_by_space(l)

            if len(parts) != 2:
                # TODO
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
                    print(original)
                    assert original.endswith('<number>')

                self.options.append(IntegerRangeFlag(key, min, max))
            else:
                print('WARNING: parsing error: ' + l)
                # TODO
                pass

    def parse_params(self):
        for l in output_for_command('%s -Q --help=params %s' % (get_compiler(), self.level)):
            if l == '':
                continue
            parts = split_by_space(l)

            assert len(parts) == 7
            self.options.append(Param(parts[0], parts[1:]))

    def add_interesting_options(self):
        sanitize_values = 'address,kernel-address,thread,leak,undefined,vptr,shift,integer-divide-by-zero,unreachable,vla-bound,null,return,signed-integer-overflow,bounds,bounds-strict,alignment,object-size,float-divide-by-zero,float-cast-overflow,nonnull-attribute,returns-nonnull-attribute,bool,enum'.split(',')
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
            compiler = get_compiler_by_extension(source_file)

            # TODO: warning
            cmd = 'timeout %d %s -c %s -I/home/marxin/BIG/Programming/llvm-project/libcxx/test/support/ -Wno-overflow %s %s %s -o/dev/null' % (args.timeout, compiler, args.cflags, self.level, source_file, ' '.join(options))
            r = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            if r.returncode != 0:
                global failed_tests
                failed_tests += 1
                try:
                    stderr = r.stderr.decode('utf-8')
                    ice = find_ice(stderr)
                    # TODO: remove
                    if ice != None and not ice[1] in ice_cache and not any([x in ice[0] for x in known_bugs.keys()]):
                        ice_locations.add(ice[0])
                        ice_cache.add(ice[1])
                        print(colored('NEW ICE #%d: %s' % (len(ice_cache), ice[0]), 'red'))
                        print(cmd)
                        print(ice[1])
                        print()
                        self.reduce(cmd)
                        sys.stdout.flush()
                    elif args.logging:
                        logging.debug(cmd)
                        logging.debug(stderr)
                except UnicodeDecodeError as e:
                    print('ERROR: !!!cannot decode stderr!!!')
                if r.returncode == 124 and args.verbose:
                    print(colored('TIMEOUT:', 'red'))
                    print(cmd)
        except Exception as e:
            print('FATAL ERROR')
            traceback.print_exc(file = sys.stdout)

    def reduce(self, cmd):
        r = subprocess.run(os.path.join(script_dir, "gcc-reduce-flags.py") + " '" + cmd + "'", shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        assert r.returncode == 0
        reduced_command = r.stdout.decode('utf-8').strip()
        print('Reduced command: ' + reduced_command)
        # TODO: fix me please
        # self.reduce_testcase(reduced_command)

    def reduce_testcase(self, cmd):
        parts = cmd.split(' ')
        f = parts[1]
        compiler = get_compiler_by_extension(f)
        assert compiler != None

        if not compiler.endswith('gcc') and not compiler.endswith('g++'):
            return

        suffix = '.i' if compiler.endswith('gcc') else '.ii'

        r = subprocess.run(cmd + ' -E', shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
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
        r = subprocess.run('creduce --n 10 %s %s' % (reduce_script.name, source_filename), shell = True, stdout = subprocess.PIPE)
        assert r.returncode == 0
        lines = r.stdout.decode('utf-8').split('\n')
        lines = list(dropwhile(lambda x: not '*******' in x, lines))
        print('\n'.join(lines))
        print(colored('CREDUCE ', 'cyan'), end = '')
        print('took %s s, to test:\n%s %s' % (str(time() - start), c, source.name))

os.chdir('/tmp/')
levels = [OptimizationLevel(x) for x in ['', '-O0', '-O1', '-O2', '-O3', '-Ofast', '-Os', '-Og']]

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
            speed = c / (time() - start)
            remaining = args.iterations * N - c
            print('progress: %d/%d, failed: %.2f%%, %.2f tests/s, remaining: %d, ETA: %s' % (c, args.iterations * N, 100.0 * failed_tests / c, speed, remaining, str(timedelta(seconds = round(remaining / speed )))))
            sys.stdout.flush()

print('=== SUMMARY ===')
for i in ice_locations:
    print('ICE: %s' % i)

exit(len(ice_locations) != 0)
