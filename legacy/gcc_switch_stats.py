#!/usr/bin/env python3

import os
import sys
import hashlib

from itertools import *
from operator import itemgetter

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

def average(values):
    return 1.0 * sum(values) / len(values)

def get_histogram(values, ranges, text, graph, label_x):
    buckets = [0] * (len(ranges) + 1)

    l = len(values)
    for v in values:
        v = v[1]
        seen = False
        for i in range(len(ranges)):
            r = ranges[i]
            if type(r) is int:
                if v == r:
                    buckets[i] += 1
                    seen = True
                    break
            else:
                assert len(r) == 2
                if r[0] <= v and v <= r[1]:
                    buckets[i] += 1
                    seen = True
                    break

        if not seen:
            buckets[-1] += 1

    print('HISTOGRAM: %s' % text)
    keys = []
    values = []
    for i, b in enumerate(buckets):
        name = str(ranges[i]) if i < len(ranges) else 'other'
        keys.append(name)
        v = b / l
        values.append(v)
        print('%10s: %6.2f%% %10d' % (name, 100.0 * v, b))

    # generate graph
    x = range(len(keys))

    fig, ax = plt.subplots()
    ax.set_title(text)
    ax.set_xlabel(label_x)
    ax.set_ylabel('switches')
    plt.bar(x, values)
    plt.xticks(x, keys)
    plt.xticks(rotation=70)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:.0%}'.format(y)))         
    plt.tight_layout()

    plt.tight_layout()
    plt.savefig(graph, dpi = 300)

class Case:
    def __init__(self, line):
        self.failed = False

        tokens = line.split(':')
        if len(tokens) != 2:
            self.failed = True
            return

        c = tokens[0][5:]
        r = c.split('..')

        try:
            if len(r) == 1:
                self.low = int(c)
                self.high = self.low
            else:
                self.low = int(r[0])
                self.high = int(r[1])

            self.bb = int(tokens[1][3:])
        except ValueError as e:
            self.failed = True
            return

        # can happen when having an overwritten
        if self.low > self.high:
            self.failed = True

    def __repr__(self):
        s = ('%d..%d' % (self.low, self.high)) if self.low != self.high else str(self.low)
        return 'case %s: bb_%d' % (s, self.bb)

class Type:
    def __init__(self, line, enum_values):
        parts = line.split(',')
        assert len(parts) == 2

        self.precision = int(parts[0].split(':')[1])
        self.unsigned = int(parts[1].split(':')[1])
        self.enum_values = None
        self.enum_values_count = -1

        if enum_values != None:
            parts = enum_values.split(' ')
            n = parts[0]
            i = n.find('(')
            n = int(n[i+1:-2])
            self.enum_values_count = n

            parts = parts[1:]
            self.enum_values = []
            for part in parts:
                t = part.split('...')
                if len(t) == 1:
                    t = int(t[0])
                    self.enum_values.append((t, t))
                else:
                    self.enum_values.append((int(t[0]), int(t[1])))

            # sort enum values
            self.enum_values = sorted(self.enum_values, key = lambda x: x[0])

    def verify(self):
        if self.enum_values != None:
            n = sum([x[1] - x[0] + 1 for x in self.enum_values])
            return n == self.enum_values_count

            l = len(self.enum_values)
            for i in range(l):
                e = self.enum_values[i]
                assert e[0] <= e[1]
                if l > 1 and i < l - 1:
                    assert e[1] < self.enum_values[i + 1][0] and [1] + 1 != self.enum_values[i + 1]

        return True

    def is_enum(self):
        return self.enum_values != None

    def is_contiguous(self):
        return len(self.enum_values) == 1

    def get_range(self):
        return (self.enum_values[0][0], self.enum_values[-1][1])

    def get_enum_size(self):
        return sum([c[1]- c[0] + 1 for c in self.enum_values])

    def handles_value(self, value):
        for e in self.enum_values:
            if e[0] <= value and value <= e[1]:
                return True

        return False

    def print(self):
        print('enum_values (%d): %s' % (self.enum_values_count, str(self.enum_values)))

    def get_type_info(self):
        return '%s %d' % ('unsigned' if self.unsigned else 'signed', self.precision)

class Switch:
    def __init__(self, line, package):
        assert package.endswith('.log')
        self.package = package[:-4]
        self.file = None
        self.line = None
        self.column = None
        self.failed = False
        self.histogram = None
        self.histogram_sorted = None
        self.histogram_sum = None

        self.parse(line)

    def parse(self, line):
        token = 'note: SWITCH_STATEMENT:'
        i = line.find(token)
        if i == -1:
            self.failed = True
            return

        part1 = line[:i].strip()
        part2 = line[i + len(token):].strip()

        if (part1 != ''):
            x = part1.rfind(' ')
            if x != -1:
                part1 = part1[x + 1:]
            location = part1.split(':')
            if len(location) == 4:
                self.file = location[0]
                self.line = location[1]
                self.column  = location[2]

        if not part2.startswith('default:') or not part2.endswith('#'):
            self.failed = True
            return

        part2 = part2.rstrip('#')

        tokens = part2.split('#')
        if len(tokens) < 2:
            self.failed = True
            return

        spart = tokens[0].strip()
        tpart = tokens[1]

        cases = spart.split(' ')

        # handle default
        self.default = int(cases[0].split(':')[1][3:])
        cases = cases[1:]

        # handle cases
        self.cases = [Case(x) for x in cases]

        for c in self.cases:
            if c.failed:
                self.failed = True
                return

        # verify cases
        self.cases = sorted(self.cases, key = lambda c: c.low)
        l = len(self.cases)
        for i in range(l):
            c = self.cases[i]
            assert c.low <= c.high
            if l > 1 and i < l - 1:
                if not (c.high < self.cases[i + 1].low):
                    self.failed = True
                    return

        # handle type info
        token = 'ENUM_VALUES'
        enum_values = None
        i = tpart.find(token)
        if i != -1:
            enum_values = tpart[i:].strip()
            tpart = tpart[:i]

        self.type = Type(tpart, enum_values)
        if not self.type.verify():
            self.failed = True
            return

        # handle histogram
        if len(tokens) == 3:
            h = tokens[2]
            assert h.startswith('SWITCH_HISTOGRAM')
            parts = h.split(' ')
            assert len(parts) == 2
            array = parts[1][1:-1]
            values = [int(x) for x in array.split(',')]
            assert len(values) == len(self.cases) + 1
            self.histogram = values
            self.histogram_sorted = sorted(self.histogram, reverse = True)
            self.histogram_sum = sum(self.histogram)

        assert len(self.cases) > 0

    def get_range(self):
        return (self.cases[0].low, self.cases[-1].high)

    def get_range_size(self):
        r = self.get_range()
        return r[1] - r[0] + 1

    def get_covered_values(self):
        return sum([c.high - c.low + 1 for c in self.cases])

    def get_density(self):
        return 1.0 * self.get_covered_values() / self.get_range_size()

    def has_range(self):
        for c in self.cases:
            if c.low != c.high:
                return True

        return False

    def get_uniq_bb_count(self):
        return len(set([c.bb for c in self.cases]))

    def has_all_bbs_uniq(self):
        bbs = [c.bb for c in self.cases] + [self.default]
        return len(bbs) == len(set(bbs))

    def get_bb_density(self):
        return 1.0 * self.get_uniq_bb_count() / len(self.cases)

    def handles_value(self, value):
        for c in self.cases:
            if c.low <= value and value <= c.high:
                return True

        return False

    def get_all_values(self):
        for c in self.cases:
            for i in range(c.low, c.high + 1):
                yield i

    def is_power_of_2(self):
        for v in self.get_all_values():
            if v == 0 or (v & (v - 1)) == 0:
                continue
            else:
                return False

        return True

    def is_multiply_values(self):
        start = None
        max = None

        if self.handles_value(0):
            return False

        for v in self.get_all_values():
            max = v
            if v == 0:
                continue
            elif v == 1 or v == -1:
                return False

            if start == None:
                start = v

            if v % start != 0:
                return False

            max = v

        if max <= 1 or max == start:
            return False

        if start <= 2:
            return False

        return True

    def has_enum_and_ranges_diff(self):
        if self.type.enum_values == None:
            return False

        for c in self.cases:
            if not self.type.handles_value(c.low):
                return True
            elif not self.type.handles_value(c.high):
                return True

#        for e in self.type.enum_values:
#            if not self.handles_value(e[0]):
#                return True
#            elif not self.handles_value(e[1]):
#                return True

        return False

    def __repr__(self):
        s = 'default: bb_%d %s' % (self.default,' '.join([str(c) for c in self.cases]))
        if self.histogram:
            s += ' {%s}' % (','.join([str(x) for x in self.histogram]))
            if self.histogram_sum > 0:
                top = self.get_topn_histogram_frequency(1)
                s += ' top_frequency: %.2f%%' % (100 * top)
                if top == self.get_default_histogram_frequency():
                    s += ' is default BB'

                if not self.has_all_bbs_uniq():
                    s += ' (not all BB uniq)'

        return s

    def get_location(self):
        return '%s:%s:%s' % (self.file, self.line, self.column)

    def get_full_name(self):
        return self.get_location() + ': ' + str(self)

    def get_md5_hash(self):
        m = hashlib.md5()
        m.update(self.get_full_name().encode('utf-8'))
        return m.hexdigest()

    def has_case_equal_to_default(self):
        for c in self.cases:
            if c.bb == self.default:
                return True

        return False

    def remove_cases_to_default(self):
        self.cases = [c for c in self.cases if c.bb != self.default]

    def get_histogram_max(self):
        return max(self.histogram)

    def get_topn_histogram_frequency(self, n):
        s = sum(self.histogram_sorted[:n])
        return 1.0 * s / self.histogram_sum

    def get_top_non_default_histogram_frequency(self):
        s = max(self.histogram[1:])
        return 1.0 * s / self.histogram_sum

    def get_default_histogram_frequency(self):
        return 1.0 * self.histogram[0] / self.histogram_sum

if len(sys.argv) < 2:
    print('Usage: gcc_switch_parser.py [file] [N]')
    exit(1)

d = sys.argv[1]
limit = 0
if len(sys.argv) >= 3:
    limit = int(sys.argv[2])

files = os.listdir(d)

print('Processing %d files in %s' % (len(files), d))

switches = []
warnings = 0

# print('TODO: unlimit me!!!')
# files = files[:2000]

for f in files:
    for line in open(os.path.join(d, f)):
        line = line.strip()

        if not 'note: SWITCH' in line:
            continue

        switch = Switch(line, f)
        if switch.failed:
            warnings += 1
            continue

        switches.append(switch)

switches_count = len(switches)
print('Ignored switch statements: %d' % warnings)

print('Parsed switches: %d' % switches_count)

hash_switches = sorted(switches, key = lambda s: s.get_md5_hash())
sorted_groups = []

for k, v in groupby(hash_switches, key = lambda s: s.get_md5_hash()):
    v = list(v)
    sorted_groups.append((v[0], len(v)))

sorted_groups = sorted(sorted_groups, key = lambda x: x[1], reverse = True)
print('\nMost repeated:')
for s in [s for s in sorted_groups if s[1] > 1][:20]:
    print('%d %s' % (s[1], s[0].get_location()))
print()

switches = [x[0] for x in sorted_groups]
switches_count = len(switches)

print('Unique parsed switches: %d' % switches_count)

shared_with_default = [s for s in switches if s.has_case_equal_to_default()]
print('Switches with a shared BB with default: %d' % len(shared_with_default))

for s in shared_with_default[:limit]:
    print(s)
    s.remove_cases_to_default()
print()

types = sorted([s.type.get_type_info() for s in switches])
types_histogram = []
for k, v in groupby(types):
    types_histogram.append((k, len(list(v))))

print('Switch types')
for t in sorted(types_histogram, key = lambda x: x[1], reverse = True):
    print('%10d %s' % (t[1], t[0]))

print()
switches_with_range = [s for s in switches if s.has_range()]
print('Switches with a range in a case: %d (%.2f%%)' % (len(switches_with_range), 100.0 * len(switches_with_range) / switches_count))

switches_with_enum = [s for s in switches if s.type.is_enum()]
print('Switches on an enum type: %d (%.2f%%)' % (len(switches_with_enum), 100.0 * len(switches_with_enum) / switches_count))
switches_with_cont_enum = [s for s in switches_with_enum if s.type.is_contiguous()]
print('Switches on an contiguous enum type: %d (%.2f%%)' % (len(switches_with_cont_enum), 100.0 * len(switches_with_cont_enum) / switches_count))

switches_with_enum_out = [s for s in switches_with_enum if s.has_enum_and_ranges_diff()]
print('Switches with out of bounds enum check: %d (%.2f%%)' % (len(switches_with_enum_out), 100.0 * len(switches_with_enum_out) / switches_count))


switch_with_all = [s for s in switches_with_enum if s.get_covered_values() == s.type.get_enum_size()]
print('Switches with covered of all enum values: %d (%.2f%%)' % (len(switch_with_all), 100.0 * len(switch_with_all) / switches_count))

# TODO
# for s in switches_with_enum_out:
#    print(s)
#    print(s.type.print())

packages_with_switch = []
key = lambda x: x.package
for (k, v) in groupby(sorted(switches, key = key), key):
    v = list(v)
    packages_with_switch.append((v[0], len(v)))

packages_with_switch = sorted(packages_with_switch, key = lambda v: v[1], reverse = True)
print('\nPackage with most switches:')

for s in packages_with_switch[:limit]:
    print('%d %s' % (s[1], s[0].package))
print()

# dump packages with no report
#print(files)
#for f in files:
#    package = f[:-4]
#
#    print(package + (': YES' if package in packages_with_any_switch else ': NO'))

print('# packages with a switch: %d' % len(packages_with_switch))
print('Average number of switches per package: %d' % (switches_count / len(packages_with_switch)))

cases_counts = [(s, len(s.cases)) for s in switches]
print('Non-default cases count: %d' % sum([x[1] for x in cases_counts]))

print('Average # of non-default cases: %.2f' % average([len(s.cases) for s in switches]))
print('Average # of covered values: %.2f' % average([s.get_covered_values() for s in switches]))
print('Average range # of non-default cases: %.2f' % average([len(s.cases) for s in switches]))
print('Average density: %.2f' % average([100.0 * s.get_density() for s in switches]))
print('Average BB density: %.2f' % average([s.get_bb_density() for s in switches]))
all_uniq_bbs_switches = [s for s in switches if s.has_all_bbs_uniq()]
print('Switches with all unique BBs: %d (%.2f%%)' % (len(all_uniq_bbs_switches), 100.0 * len(all_uniq_bbs_switches) / switches_count))

percentage_by_10 = [[0, 10], [11, 20], [21, 30], [31, 40], [41, 50], [51, 60], [61, 70], [71, 80], [81, 90], [91, 100]]

switches_with_hist = [s for s in switches if s.histogram and s.histogram_sum != 0]
if len(switches_with_hist) != 0:
    print()
    print('Switches with a non-zero histogram: %d (%.2f%%)' % (len(switches_with_hist), 100.0 * len(switches_with_hist) / switches_count))
    print('Average # of executions: %.2E' % average([s.histogram_sum for s in switches_with_hist]))

    histogram_default_frequency = [(s, round(100.0 * s.get_default_histogram_frequency())) for s in switches_with_hist]
    print('Average frequency of default: %d%%' % average([x[1] for x in histogram_default_frequency]))
    histogram_max_frequency = [(s, round(100.0 * s.get_topn_histogram_frequency(1))) for s in switches_with_hist]
    histogram_max_nondefault_frequency = [(s, round(100.0 * s.get_top_non_default_histogram_frequency())) for s in switches_with_hist]
    print('Average frequency of most common value: %d%%' % average([x[1] for x in histogram_max_frequency]))
    print('Average frequency of most common (non-default) value: %d%%' % average([x[1] for x in histogram_max_nondefault_frequency]))
    print('Average frequency of top 2 max values: %d%%' % average([round(100.0 * s.get_topn_histogram_frequency(2)) for s in switches_with_hist]))
    print('Average frequency of top 3 max values: %d%%' % average([round(100.0 * s.get_topn_histogram_frequency(3)) for s in switches_with_hist]))

    print()
    get_histogram(histogram_max_frequency, percentage_by_10, 'Frequency of most common case', 'top_frequency.svg', 'frequency')

    print()
    get_histogram(histogram_max_nondefault_frequency, percentage_by_10, 'Frequency of most common non-default case', 'top_non_default_frequency.svg', 'frequency')

    histogram_default_frequency = [(s, round(100.0 * s.get_default_histogram_frequency())) for s in switches_with_hist]
    print()
    get_histogram(histogram_default_frequency, percentage_by_10, 'Frequency of default BB', 'default_frequency.svg', 'frequency')

    print()
    print('Examples with highes max frequency (>= 100 executions):')
    for s in sorted(filter(lambda x: x[0].histogram_sum > 100, histogram_max_frequency), key = itemgetter(1), reverse = True)[:limit]:
        print(s[0].get_full_name())
    print()

    print()
    print('Examples with the biggest # of executions:')
    for s in sorted([(s, s.histogram_sum) for s in switches_with_hist], key = itemgetter(1), reverse = True)[:limit]:
        print('%.2E: %s' % (s[1], s[0].get_full_name()))
    print()

print()
get_histogram(cases_counts, [1, 2, 3, 4, [5,8], [9, 16], [17, 32]], 'Number of non-default cases', 'cases_distribution.svg', '# of non-default cases')

print()
bbs_counts = [(s, s.get_uniq_bb_count()) for s in switches]
get_histogram(bbs_counts, [1, 2, 3, 4, [5,8], [9, 16], [17, 32]], 'Number of non-default BBs', 'bbs_distribution.svg', '# of non-default BBs')

print()
range_sizes = [(s, s.get_range_size()) for s in switches]
get_histogram(range_sizes, [1, 2, 3, 4, [5,8], [9, 16], [17, 32], [33, 64], [65, 256]], 'Switch range size', 'switch_range_size.svg', 'range size')

print()
density = [(x[0], round(x[1])) for x in [(s, 100 * s.get_density()) for s in switches]]
get_histogram(density, percentage_by_10, 'Switch density', 'density.svg', 'density')

# calculate size saving when using double indirection
to256 = [s for s in range_sizes if s[1] <= 256]
PTR_SIZE = 8

jt_sizes = []
improvements = []
for s in to256:
    before = PTR_SIZE * s[1]
    jt_sizes.append(before)
    after = s[1] + PTR_SIZE * s[0].get_uniq_bb_count()
    if after < before:
        improvements.append(1.0 * after / before)

print()
print('For all cases with range <= 256: %d (%.2f%%), beneficial to double transformation: %d (%.2f%%)' % (len(to256), 100.0 * len(to256) / switches_count, len(improvements), 100.0 * len(improvements) / len(to256)))
print('Average improvement: %.2f%%' % (100.0 * average(improvements)))
print('Average jump table size before: %.2f B' % average(jt_sizes))

# test if cases are power of 2
powers_of_2_switches = []
for s in switches:
    if s.is_power_of_2() and s.get_covered_values() >= 4:
        powers_of_2_switches.append(s)

print('Power of 2 switches (and covered values >= 4): %d (%.2f%%)' % (len(powers_of_2_switches), 100.0 * len(powers_of_2_switches) / switches_count))

for s in powers_of_2_switches[:limit]:
    print(s)
print()

cases_counts = [(s, len(s.cases)) for s in powers_of_2_switches]
get_histogram(cases_counts, [1, 2, 3, 4, [5,8], [9, 16], [17, 32]], 'Number of cases for 2^N case values', 'power_of_2.svg', '# of non-default cases')

# test if cases multiple of first non-zero value
multiplies = []
power2_set = set(powers_of_2_switches)
for s in switches:
    if s.is_multiply_values() and not s in power2_set and len(s.cases) > 3:
        multiplies.append(s)

print()
print('Multiply switches: %d (%.2f%%)' % (len(multiplies), 100.0 * len(multiplies) / switches_count))

for s in multiplies[:limit]:
    print(s)
print()

cases_counts = [(s, len(s.cases)) for s in multiplies]
get_histogram(cases_counts, [1, 2, 3, 4, [5,8], [9, 16], [17, 32]], 'Number cases being a multiply of first one', 'multiply.svg', '# of non-default cases')

print()
print('Switches with range <= 64 and a duplicate BB we can do bit tests')
small_range = [s for s in switches if s.get_range_size() <= 64 and s.get_uniq_bb_count() < s.get_covered_values()]
small_range_by_density = sorted([(s, s.get_bb_density()) for s in small_range], key = lambda x: x[1])

print('Candidates: %d (%.2f%%)' % (len(small_range), 100.0 * len(small_range) / switches_count))
print('Average BB density of these switches: %.2f' % average([s.get_bb_density() for s in small_range]))
threshold = 0.5
filtered = list(filter(lambda x: x[1] <= threshold, small_range_by_density))
print('Candidates with density < %.2f : %d (%.2f%%)' % (threshold, len(filtered), 100.0 * len(filtered) / switches_count))

print('Example: ')
for s in small_range_by_density[:limit]:
    print('%.2f    %s' % (s[1], s[0]))
print()
