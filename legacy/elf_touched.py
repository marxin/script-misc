#!/usr/bin/env python3

import sys
import argparse
import json
import os
import re

from functools import *

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.relocation import RelocationSection
from elftools.elf.descriptions import *

class ElfSymbol:
    def __init__(self, name, type, offset, size):
        self.name = name
        self.type = type
        self.offset = offset
        self.size = size

class ElfSection:
    def __init__(self, name, offset, size):
        self.name = name
        self.offset = offset
        self.size = size
        self.symbols = []

    def get_symbol_by_addr(self, addr):
        for s in self.symbols:
            if s.offset <= addr and addr < s.offset + s.size:
                return s
        return None

class ElfInfo:
    def __init__(self, path):
        self.path = path
        self.sections = []

        self.parse_sections()
        self.dump()
        self.parse_symbols()

    def parse_sections(self):
        with open(self.path, 'rb') as f:
            elffile = ELFFile(f)

            for section in elffile.iter_sections():
                addr = section['sh_addr']
                if addr > 0:
                    self.sections.append(ElfSection(section.name, addr, section['sh_size']))

    def get_section_by_addr(self, addr):
        for s in self.sections:
            if s.offset <= addr and addr < s.offset + s.size:
                return s
        return None

    def find_symbol_by_addr(self, addr):
        section = self.get_section_by_addr(addr)
        if section:
            return section.get_symbol_by_addr(addr)

    def simulate(self, icegrind_file):
        seen = set()
        counter = 1

        for l in open(icegrind_file, 'r').readlines():
            if l.startswith('ma:'):
                addr = int(l.split(':')[1], 16)
                symbol = self.find_symbol_by_addr(addr)
                if symbol:
                    if not symbol in seen:
                        seen.add(symbol)
                        print('visit %3d:%10s:%s' % (counter, symbol.type, symbol.name))
                        counter += 1

    def parse_symbols(self):
        with open(self.path, 'rb') as f:
            elffile = ELFFile(f)

            symbol_tables = [s for s in elffile.iter_sections() if isinstance(s, SymbolTableSection)]
            for section in symbol_tables:
                if section.name != '.symtab':
                    continue

                for nsym, symbol in enumerate(section.iter_symbols()):
                    shndx = describe_symbol_shndx(symbol['st_shndx'])
                    if shndx == 'UND':
                        continue

                    name = symbol.name
                    if name == '':
                        continue

                    offset = symbol['st_value']
                    if offset == 0:
                        continue

                    size = symbol['st_size']
                    t = describe_symbol_type(symbol['st_info']['type'])
                    if t == 'NOTYPE':
                        continue

                    section = self.get_section_by_addr(offset)
                    if section == None:
                        print('Warning: cannot find section for: %s/%d' % (name, offset))
                    else:
                        section.symbols.append(ElfSymbol(name, t, offset, size))

    def dump(self):
        for s in self.sections:
            print('%s:%d:%d, symbols: %d' % (s.name, s.offset, s.size, len(s.symbols)))
            for symbol in s.symbols[:10]:
                print('  ' + symbol.name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Print info about touched parts of an ELF file')
    parser.add_argument('elf_file', metavar = 'elf_file', help = 'ELF file')
    parser.add_argument('icegrind_log', metavar = 'icegrind_log', help = 'icegrind log file')
    args = parser.parse_args()

    elfinfo = ElfInfo(args.elf_file)
    elfinfo.dump()
    print()
    elfinfo.simulate(args.icegrind_log)
