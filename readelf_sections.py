#!/usr/bin/env python3

import sys
import hashlib
import argparse
import json
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.relocation import RelocationSection

class MySection:
    def __init__(self, name, size, digest, relocations = 0, symbols = 0):
        self.name = name
        self.size = size
        self.md5sum = digest

class ElfInfo:
    def __init__(self, path):
        self.path = path
        self.content = open(path, 'rb').read()

        self.file_size = len(self.content)
        self.file_md5sum = hashlib.md5(self.content).hexdigest()
        self.sections_sum = 0
        self.sections = []

        self.num_relocations = 0
        self.num_symbols = 0
        self.debug_sections_size = 0

        self.parse()

    def parse(self):
        with open(self.path, 'rb') as f:
            elffile = ELFFile(f)

            for section in elffile.iter_sections():
                name = section.name.decode('utf-8')
                size = section['sh_size']
                digest = hashlib.md5(section.data()).hexdigest()
                self.sections_sum += size

                if isinstance(section, SymbolTableSection):
                    self.num_symbols += section.num_symbols()

                if isinstance(section, RelocationSection):
                    self.num_relocations += section.num_relocations()

                if name.startswith('.debug'):
                    self.debug_sections_size += size

                self.sections.append(MySection(name, size, digest))

    def dump(self):
        content = { 'file_size': self.file_size,
            'sections_size': self.sections_sum,
            'md5sum': self.file_md5sum,
            'sections': [x.__dict__ for x in self.sections],
            'relocations': self.num_relocations,
            'symbols': self.num_symbols,
            'debug_sections_size': self.debug_sections_size,
            'stripped_sections_size': self.sections_sum - self.debug_sections_size,
            'filename': os.path.abspath(self.path) }

        print(json.dumps(content, indent = 2, sort_keys = True))

    def compare(self, other):
        print('Comparing: %s vs. %s' % (self.path, other.path))
        if self.num_symbols != other.num_symbols:
            print('  number of symbols does not match: %d/%d' % (self.num_symbols, other.num_symbols))

        if len(self.sections) != len(other.sections):
            print('  number of sections does not match: %d/%d' % (len(self.sections), len(other.sections)))
        else:
            for i, s in enumerate(self.sections):
                s2 = other.sections[i]
                if s.name != s2.name:
                    print('  section names does not match: %s/%s' % (s.name, s2.name))
                else:
                    if s.size != s2.size:
                        print('  section %s: sizes does not match: %d/%d' % (s.name, s.size, s2.size))
                    elif s.md5sum != s2.md5sum:
                        print('  section %s: md5sum does not match' % (s.name))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display statistics about binaries.')
    parser.add_argument('file', metavar = 'file', help = 'ELF file')
    parser.add_argument('--compared', metavar = 'compared', help = 'Compared ELF file', default = None)

    args = parser.parse_args()

    if args.compared == None:
        elfinfo = ElfInfo(args.file)
        elfinfo.dump()
    else:
        elfinfo1 = ElfInfo(args.file)
        elfinfo2 = ElfInfo(args.compared)

        elfinfo1.compare(elfinfo2)
