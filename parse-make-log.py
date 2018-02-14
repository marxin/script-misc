#!/usr/bin/env python3

# SAMPLE output:
# Removing child 0x751790 PID 2690 from chain.
# Putting child 0x750660 (all-libiberty) PID 2693 on the chain. Timestamp: 1518616574 443501
# Live child 0x750660 (all-libiberty) PID 2693 
# make[1]: Entering directory '/home/marxin/Programming/gcc-4.1.2-20070115/objdir/libiberty'
# if [ x"" != x ] && [ ! -d pic ]; then \
#   mkdir pic; \
# else true; fi
# Putting child 0x68f5a0 (stamp-picdir) PID 2711 on the chain. Timestamp: 1518616574 453184
# Live child 0x68f5a0 (stamp-picdir) PID 2711 
# Reaping winning child 0x68f5a0 PID 2711 . Timestamp: 1518616574 454740
# touch stamp-picdir
# Live child 0x68f5a0 (stamp-picdir) PID 2712 
# Reaping winning child 0x68f5a0 PID 2712 . Timestamp: 1518616574 455676

import sys
import os

class Target:
    def __init__(self, name, start, command, pid):
        self.name = name
        self.start = start
        self.command = command
        self.pid = pid
        self.end = None

    def duration(self):
        assert self.end >= self.start
        return self.end - self.start

if len(sys.argv) != 2:
    print('Usage: <file>')
    exit(1)

lines = [x.strip() for x in open(sys.argv[1]).readlines()]

targets = []

for i, l in enumerate(lines):
    if l.startswith('Putting child'):
        parts = l.split(' ')
        target = parts[3][1:-1]
        timestamp = float(parts[-2]) + float(parts[-1]) / 1000000
        assert parts[-3] == 'Timestamp:'
        j = i - 1
        command = []
        while j >= 0:
            if ' child ' in lines[j]:
                break
            command.insert(0, lines[j])
            j -= 1

        command = '\n'.join(command)
        assert parts[4] == 'PID'
        pid = int(parts[5])
        targets.append(Target(target, timestamp, command, pid))
    elif l.startswith('Reaping winning child'):
        parts = l.split(' ')
        timestamp = float(parts[-1])
        timestamp = float(parts[-2]) + float(parts[-1]) / 1000000
        assert parts[-3] == 'Timestamp:'
        pid = int(parts[5])

        if targets[-1].pid == pid:
            targets[-1].end = timestamp

print('Parsed targets: %d ' % len(targets))
# print('Skipped: ')
# for t in targets:
#     if t.end == None:
#         print('  ' + t.name)

print()
targets = sorted([x for x in targets if x.end != None], key = lambda x: x.duration(), reverse = True)

for t in targets:
    if t.duration() > 0.1 and not t.name.startswith('configure-'):
        s = '%.2fs' % t.duration()
        print('%36s: %7s' % (t.name, s))
