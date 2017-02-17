#!/usr/bin/env python3

import argparse
import subprocess
import random
import sys
import glob

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
source_files = glob.glob('/home/marxin/Programming/gcc/**/pr[0-9]*.c', recursive = True)

def split_by_space(line):
    return [x for x in line.replace('\t', ' ').split(' ') if x != '']

def output_for_command(command):
    r = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    assert r.returncode == 0
    lines = [x.strip() for x in r.stdout.decode('utf-8').split('\n') if x.strip() != '']
    lines = lines[1:]
    return lines

def check_option(level, option):
    if option in option_validity_cache:
        return option_validity_cache[option]

    cmd = 'gcc -c /tmp/empty.c %s %s' % (level, option)
    r = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    result = r.returncode == 0
    option_validity_cache[option] = result
    return result

def switch_option(option):
    assert option.startswith('-f') or option.startswith('-m')
    prefix = option[:2]
    option = option[2:]
    if option.startswith('no-'):
        return prefix + option[3:]
    else:
        return prefix + 'no-' + option

class OptimizationLevel:
    def __init__(self, level):
        self.level = level
        self.enabled = []
        self.disabled = []

        self.parse_options('target')        
        self.parse_options('optimize')

        self.enabled = self.filter_options(self.enabled)
        self.disabled= self.filter_options(self.disabled)

    def parse_options(self, name):
        for l in output_for_command('gcc -Q --help=%s %s' % (name, self.level)):
            parts = split_by_space(l)

            if len(parts) != 2:
                # TODO
                continue

            key = parts[0]
            value = parts[1]

            # TODO: report bug
            if key == '-m3dnowa':
                continue

            # TODO: report bug #2
            if key == '-msse' or key == '-mfp-ret-in-387' or key == '-m80387':
                continue

            # TODO: report bug #3
            if key == '-fselective-scheduling2':
                continue

            if key == '-miamcu':
                continue

            if value == '[enabled]':
                self.enabled.append(key)
            elif value == '[disabled]':
                self.disabled.append(key)
            else:
                # TODO
                pass        

    def filter_options(self, l):
        filtered = []

        for o in self.enabled + self.disabled:
            r = check_option(self.level, o)
            assert r
               
            # switch option
            s = switch_option(o)
            r = check_option(self.level, s)
            if not r:
                print('failed: ' + s)
            else:
                filtered.append(o)

        return filtered

    def test(self, option_count):
        options = []

        for i in range(option_count):
            if random.choice([True, False]):
                options.append(switch_option(random.choice(self.enabled)))
            else:
                options.append(random.choice(self.disabled))

        # TODO: warning
        cmd = 'gcc -c -Wno-overflow %s %s %s' % (self.level, random.choice(source_files), ' '.join(options))
        r = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        if r.returncode != 0:
            print('\n' + cmd)
            print(r.stderr.decode('utf-8'))
        else:
            print('.' , end = '')
            sys.stdout.flush()

levels = [OptimizationLevel(x) for x in ['', '-O0', '-O1', '-O2', '-O3', '-Ofast', '-Os', '-Og']]

for l in levels:
    print(l.level)
    print(l.enabled)
    print(l.disabled)

random.seed(11111111)
for i in range(1000 * 1000):
    level = random.choice(levels)
    level.test(random.randint(1, 20))

