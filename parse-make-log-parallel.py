#!/usr/bin/env python3

import sys
import os
import svgwrite
import math

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

targets = []
cache = {}

for i, l in enumerate(lines):
    if l.startswith('Putting child'):
        parts = l.split(' ')
        target = parts[3][1:-1]
        assert parts[4] == 'PID'
        pid = int(parts[5])
        assert not pid in cache
        cache[pid] = Target(target, pid)
    elif l.startswith('Reaping '):
        parts = l.split(' ')
        target = parts[4]
        assert parts[5] == 'PID'
        pid = int(parts[6])
        if pid in cache:
            t = cache[pid]
            start = float(parts[9]) + float(parts[10]) / 1000000
            end = float(parts[12]) + float(parts[13]) / 1000000
            t.start = start
            t.end = end
            targets.append(t)
            del cache[pid]

filtered = sorted([t for t in targets if t.duration() > float(sys.argv[2])], key = lambda x: x.start)
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
for i in range(200):
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
maximum_booking_id = max([x.booking_index for x in filtered])
margin = 100
height = 60
dwg = svgwrite.Drawing(sys.argv[3], size = (100 * filtered[-1].end + 2 * margin, height * (maximum_booking_id + 4)), profile = 'tiny')
dwg.add(dwg.rect(insert=(0, 0), size = ('100%', '100%'), fill = 'white'))

# draw the ruler
Y = 50
dwg.add(dwg.line(start = (margin, Y), end = (100 * filtered[-1].end + margin, Y), stroke = 'black'))
for i in range(math.ceil(filtered[-1].end)):
    dwg.add(dwg.line(start = (100 * i, Y - 10), end = (100 * i, Y + 10), stroke = 'black'))
    if i != 0:
        dwg.add(dwg.text(str(i), insert = (100 * (i + 1), Y - 30), font_size = 22))

for t in filtered:
    start_x = margin + 100.0 * t.start
    end_x = margin + 100.0 * t.end
    start_y = height * t.booking_index
    dwg.add(dwg.rect(insert=(start_x, margin + height * t.booking_index), size = (end_x - start_x, 0.8 * height),
        fill = 'rgb(216, 172, 51)', stroke = 'black'))
    dwg.add(dwg.text('%s: %.1fs' % (t.name, t.duration()), insert=(start_x, margin + start_y + height / 2), font_size = 22))

dwg.save()

#for t in filtered:
#    print('%d: %s: %f -> %f: %f' % (t.pid, t.name, t.start, t.end, t.duration()))
