#!/usr/bin/env python3

import sys
import os
import svgwrite

class Target:
    def __init__(self, name, pid):
        self.name = name
        self.pid = pid
        self.start = None
        self.end = None
        self.booking_index = None

    def duration(self):
        assert self.end >= self.start
        return self.end - self.start

if len(sys.argv) != 4:
    print('Usage: <file> <threshold> <output>')
    exit(1)

lines = [x.strip() for x in open(sys.argv[1]).readlines()]

targets = {}

for i, l in enumerate(lines):
    if l.startswith('Putting child'):
        parts = l.split(' ')
        target = parts[3][1:-1]
        assert parts[4] == 'PID'
        pid = int(parts[5])
        assert not pid in targets
        targets[pid] = Target(target, pid)
    elif l.startswith('Reaping '):
        parts = l.split(' ')
        target = parts[4]
        assert parts[5] == 'PID'
        pid = int(parts[6])
        if pid in targets:
            t = targets[pid]
            start = float(parts[9]) + float(parts[10]) / 1000000
            end = float(parts[12]) + float(parts[13]) / 1000000
            t.start = start
            t.end = end

filtered = sorted([t for (k, t) in targets.items() if t.duration() > float(sys.argv[2])], key = lambda x: x.start)
min_start = filtered[0].start

for f in filtered:
    f.start -= min_start
    f.end -= min_start

events = []
for f in filtered:
    events.append((f.start, 0, f))
    events.append((f.end, 1, f))

sorted_events = sorted(events, key = lambda x: x[0])

booking = []
for i in range(20):
    booking.append(None)

for event in sorted_events:
    if event[1] == 0:
        # start
        for i, b in enumerate(booking):
            if booking[i] == None:
                event[2].booking_index = i
                booking[i] = event[2]
#                print('At: %f adding to booking %d: %d' % (event[0], i, event[2].pid))
                break
    elif event[1] == 1:
        # end
        i = event[2].booking_index
        assert booking[i] == event[2]
        booking[i] = None
#        print('At: %f removing from booking %d: %d' % (event[0], i, event[2].pid))

# write it SVG file

dwg = svgwrite.Drawing(sys.argv[3], profile='tiny')
dwg.add(dwg.rect(insert=(0, 0), size = ('100%', '100%'), fill = 'white'))

for t in filtered:
    start_x = 100.0 * t.start    
    end_x = 100.0 * t.end
    height = 60
    start_y = height * t.booking_index
    dwg.add(dwg.rect(insert=(start_x, height * t.booking_index), size = (end_x - start_x, 0.8 * height),
        fill = 'rgb(216, 172, 51)', stroke = 'black'))
    dwg.add(dwg.text('%s: %.1f' % (t.name, t.duration()), insert=(start_x, start_y + height / 2), font_size = 24))

#dwg.add(dwg.line((0, 0), (10, 30), stroke=svgwrite.rgb(10, 10, 16, '%')))
#dwg.add(dwg.text('Test', insert=(10, 200), fill='red'))

dwg.save()

#for t in filtered:
#    print('%d: %s: %f -> %f: %f' % (t.pid, t.name, t.start, t.end, t.duration()))
