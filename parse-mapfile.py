#!/usr/bin/env python3

from itertools import dropwhile, takewhile

class MapComponent:
    def __init__(self, name, lines):
        self.name = name
        self.lines = lines[1:]
        self.addresses = []
        self.start = None
        self.end = None

        for l in self.lines:
            parts = [x for x in l.split(' ') if x]
            if len(parts) >= 1 and parts[0].startswith('0x0'):
                self.addresses.append(int(parts[0], 16))

    def get_address_range(self):
        if self.start and self.end and self.name and self.start != self.end:
            return (self.name, self.start, self.end)
        else:
            return None

def parse_mapfile(filename):
    components = []
    map_components = [
    (' *(.text.unlikely .text.*_unlikely .text.unlikely.*)', '.text.unlikely'),
    (' *(.text.exit .text.exit.*)', '.text.exit'),
    (' *(.text.startup .text.startup.*)', '.text.startup'),
    (' *(.text.hot .text.hot.*)', '.text.hot'),
    (' *(.text .stub .text.* .gnu.linkonce.t.*)', '.text.normal'),
    (' *(.gnu.warning)', None),
    ('.gnu.attributes', None)
    ]

    lines = [l.rstrip() for l in open(filename)]

    lines = list(dropwhile(lambda x: x != map_components[0][0], lines))
    for i in range(0, len(map_components) - 1):
        chunk = list(takewhile(lambda x: x != map_components[i+1][0], lines))
        components.append(MapComponent(map_components[i][1], chunk))
        lines = lines[len(chunk):]

    components[-1].start = components[-1].addresses[0]
    end = components[-1].start

    for i in reversed(range(len(map_components) - 1)):
        components[i].end = end
        if len(components[i].addresses):
            components[i].start = components[i].addresses[0]
            end = components[i].start

    return [c.get_address_range() for c in components if c.get_address_range()]

r = parse_mapfile('/tmp/mapfile.txt')
print(r)
