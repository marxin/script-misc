#!/usr/bin/env python3

import os
import sys

def average(values):
    return 1.0 * sum(values) / len(values)

def get_histogram(values, ranges, text):
    buckets = [0] * (len(ranges) + 1)

    l = len(values)
    for v in values:
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
    for i, b in enumerate(buckets):
        name = str(ranges[i]) if i < len(ranges) else 'other'
        print('%10s: %6.2f%%' % (name, 100.0 * b / l))

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
        return 'case %d..%d: bb_%d' % (self.low, self.high, self.bb)

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

    def verify(self):
        if self.enum_values != None:
            n = sum([x[1] - x[0] + 1 for x in self.enum_values])
            return n == self.enum_values_count

            l = len(self.enum_values)
            for i in range(l):
                e = self.enum_values[i]
                assert e[0] <= e[1]
                if l > 1 and i < l - 1:
                    assert e[1] < self.enum_values[i + 1][0]

        return True

    def print(self):
        print('enum_values (%d): %s' % (self.enum_values_count, str(self.enum_values)))

class Switch:
    def __init__(self, line, package):
        assert package.endswith('.log')
        self.package = package[:-4]
        self.file = None
        self.line = None
        self.column = None
        self.failed = False

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
        if len(tokens) != 2:
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

        assert len(self.cases) > 0

    def get_range(self):
        return (self.cases[0].low, self.cases[-1].high)

    def get_range_size(self):
        r = self.get_range()
        return r[1] - r[0] + 1

    def get_covered_values(self):
        return sum([c.high - c.low + 1 for c in self.cases])

    def get_sparsity(self):
        return 1.0 * self.get_range_size() / self.get_covered_values()

    def print(self):
        print('%s:%s:%s' % (self.file, self.line, self.column))
        self.type.print()

    def __repr__(self):
        return ' '.join([str(c) for c in self.cases])

if len(sys.argv) != 2:
    print('Usage: gcc_switch_parser.py [file]')
    exit(1)

d = sys.argv[1]
files = os.listdir(d)

print('Processing %d files in %s' % (len(files), d))

switches = []
warnings = 0

for f in files:
    for line in open(os.path.join(d, f)):
        line = line.strip()

        if not 'note: SWITCH' in line:
            continue

        s = Switch(line, f)
        if s.failed:
            warnings += 1
            continue

        switches.append(s)


print('Ignored switch statements: %d' % warnings)

print('Parsed switches: %d' % len(switches))
cases_counts = [len(s.cases) for s in switches]
print('Non-default cases count: %d' % sum(cases_counts))

print('Average # of non-default cases: %.2f' % average([len(s.cases) for s in switches]))
print('Average range # of non-default cases: %.2f' % average([len(s.cases) for s in switches]))
print('Average density: %.2f' % average([s.get_sparsity() for s in switches]))

print()
get_histogram(cases_counts, [1, 2, 3, 4, (5,8), (9, 16), (17, 32)], '# cases')

print()
bbs_counts = [len(set([c.bb for c in s.cases])) for s in switches]
get_histogram(bbs_counts, [1, 2, 3, 4, (5,8), (9, 16), (17, 32)], '# BBs')

print()
range_sizes = [s.get_range_size() for s in switches]
get_histogram(range_sizes, [1, 2, 3, 4, (5,8), (9, 16), (17, 32), (33, 64)], 'range size')

print()
sparsity = [round(x) for x in [s.get_sparsity() for s in switches] if x != 1.0]
get_histogram(sparsity, range(1, 11), 'inverted density')
