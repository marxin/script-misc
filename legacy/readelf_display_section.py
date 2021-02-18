#!/usr/bin/env python3

import sys
import hashlib
import argparse
import json
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.relocation import RelocationSection

class ElfInfo:
    def __init__(self, path, section_name):
        self.path = path
        self.content = open(path, 'rb').read()
        self.section_size = 0

        self.parse(section_name)

    def parse(self, section_name):
        with open(self.path, 'rb') as f:
            elffile = ELFFile(f)

            for section in elffile.iter_sections():
                name = section.name.decode('utf-8')
                if name == section_name:
                    self.section_size = section['sh_size']

    def dump(self):
        print('%s: %d' % (os.path.basename(self.path), self.section_size))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display info about a section of binaries.')
    parser.add_argument('section', metavar = 'section', help = 'ELF section name')
    parser.add_argument('files', metavar = 'files', help = 'ELF files', nargs='*')

    args = parser.parse_args()

    for f in args.files:
        elfinfo = ElfInfo(f, args.section)
        elfinfo.dump()
