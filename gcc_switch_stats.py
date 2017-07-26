#!/usr/bin/env python3

import sys

class Case:
    def __init__(self, line):
        tokens = line.split(':')
        assert len(tokens) == 2

        c = tokens[0][5:]
        r = c.split('..')
        if len(r) == 1:
            self.low = int(c)
            self.high = self.low
        else:
            self.low = int(r[0])
            self.high = int(r[1])

        self.bb = int(tokens[1][3:])

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

        self.verify()

    def verify(self):
        if self.enum_values != None:
            n = sum([x[1] - x[0] + 1 for x in self.enum_values])
            assert n == self.enum_values_count

    def print(self):
        print('enum_values (%d): %s' % (self.enum_values_count, str(self.enum_values)))

class Switch:
    def __init__(self, line):
        self.file = None
        self.line = None
        self.column = None

        self.parse(line)

    def parse(self, line):
        token = 'note: SWITCH_STATEMENT:'
        i = line.find(token)
        part1 = line[:i].strip()
        part2 = line[i + len(token):].strip()

        if (part1 != ''):
            location = part1.split(':')
            if len(location) == 4:
                self.file = location[0]
                self.line = location[1]
                self.column  = location[2]

        assert part2.startswith('default:')
        assert part2.endswith('#')
        part2 = part2.rstrip('#')

        tokens = part2.split('#')
        assert(len(tokens) == 2)
        spart = tokens[0].strip()
        tpart = tokens[1]

        cases = spart.split(' ')

        # handle default
        self.default = int(cases[0].split(':')[1][3:])
        cases = cases[1:]

        # handle cases
        self.cases = [Case(x) for x in cases]

        # handle type info
        token = 'ENUM_VALUES'
        enum_values = None
        i = tpart.find(token)
        if i != -1:
            enum_values = tpart[i:].strip()
            tpart = tpart[:i]

        self.type = Type(tpart, enum_values)

    def print(self):
        print('%s:%s:%s' % (self.file, self.line, self.column))
        self.type.print()

if len(sys.argv) != 2:
    print('Usage: gcc_switch_parser.py [file]')
    exit(1)

switches = []

for line in open(sys.argv[1]):
    line = line.strip()
    if not 'note: SWITCH' in line:
        continue

    switches.append(Switch(line))

print(len(switches))
