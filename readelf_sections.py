#!/usr/bin/env python3

import sys
import hashlib
import argparse
import json

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.relocation import RelocationSection

class MySection:
    def __init__(self, name, size, digest, relocations = 0, symbols = 0):
        self.name = name
        self.size = size
        self.md5sum = digest

parser = argparse.ArgumentParser(description='Display statistics about binaries.')
parser.add_argument('file', metavar = 'file', help = 'ELF file')

args = parser.parse_args()

content = open(args.file, 'rb').read()

file_size = len(content)
file_md5sum = hashlib.md5(content).hexdigest()
sections_sum = 0
sections = [] 

num_relocations = 0
num_symbols = 0
debug_sections_size = 0

with open(args.file, 'rb') as f:
    elffile = ELFFile(f)

    for section in elffile.iter_sections():
        name = section.name.decode('utf-8')
        size = section['sh_size']
        digest = hashlib.md5(section.data()).hexdigest()
        sections_sum += size

        if isinstance(section, SymbolTableSection):
            num_symbols += section.num_symbols()

        if isinstance(section, RelocationSection):
            num_relocations += section.num_relocations()

        if name.startswith('.debug'):
            debug_sections_size += size

        sections.append(MySection(name, size, digest))

content = { 'file_size': file_size, 'sections_size': sections_sum, 'md5sum': file_md5sum, 'sections': [x.__dict__ for x in sections], 'relocations': num_relocations, 'symbols': num_symbols, 'debug_sections_size': debug_sections_size, 'stripped_sections_size': sections_sum - debug_sections_size }

print(json.dumps(content, indent = 2, sort_keys = True))
