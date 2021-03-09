#!/usr/bin/env python3

import json
import subprocess
import sys

data = json.load(open('/home/marxin/Downloads/instructions.json'))
descriptions = {}


def get_description(insn):
    if insn in descriptions:
        return descriptions[insn]

    for suffix in ('b', 's', 'l', 'q'):
        if insn.endswith(suffix) and insn[:-1] in descriptions:
            return descriptions[insn[:-1]]
    return None


for extension in data['root']['extension']:
    if 'instruction' in extension:
        insns = extension['instruction']
        if isinstance(insns, dict):
            insns = [insns]
        for instruction in insns:
            asm = instruction['@asm']
            summary = instruction['@summary'] if '@summary' in instruction else None
            if asm.startswith('{') and ' ' in asm:
                asm = asm[asm.find(' ') + 1:]
            if ' ' not in asm and summary:
                descriptions[asm.lower()] = summary

histogram = {}
total = 0

proc = subprocess.run(f'objdump --no-addresses -dw --no-show-raw-insn {sys.argv[1]}',
                      shell=True, encoding='utf8', stdout=subprocess.PIPE)
lines = proc.stdout.splitlines()
for line in lines:
    if line.startswith('\t'):
        insn = line.strip().split(' ')[0]
        if insn not in histogram:
            histogram[insn] = 0
        histogram[insn] += 1
        total += 1

instructions = len(histogram)
covered = len([i for i in histogram if get_description(i)])

for insn, count in sorted(histogram.items(), key=lambda x: x[1], reverse=True):
    summary = get_description(insn)
    if not summary:
        summary = ''
    print(f'{insn:12s} {count:10d} {100.0 * count / total:.2f}% // {summary}')

print(f'Covered type of instructions: {covered}, total types: {instructions}')
