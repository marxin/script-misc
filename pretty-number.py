#!/usr/bin/env python3

import sys
from textwrap import wrap


def pad_string(s, n, prefix=''):
    if len(s) % n:
        s = '0' * (n - len(s) % n) + s
    return ' '.join(['%8s' % (prefix + x) for x in wrap(s, n)])


number = int(eval(sys.argv[1]))

print('%-20s: %d' % ('Integer', number))

hexadecimal = hex(abs(number))
assert hexadecimal.startswith('0x')
hexadecimal = hexadecimal[2:]
print('%-20s: %s' % ('Hexadecimal', pad_string(hexadecimal, 2, '0x')))
if len(hexadecimal) % 2:
    hexadecimal = '0' + hexadecimal
print('%-20s: ' % 'Integer by byte', end='')
for b in wrap(hexadecimal, 2):
    print('%8s ' % str(int(b, 16)), end='')
print()

binary = bin(abs(number))
assert binary.startswith('0b')
binary = binary[2:]
print('%-20s: %s' % ('Binary', pad_string(binary, 8)))

print('%-20s: ' % 'Bits set (0-based)', end='')
for i, v in enumerate(reversed(binary)):
    if v == '1':
        print('%d ' % i, end='')
print()
