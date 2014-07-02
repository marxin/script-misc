#!/usr/bin/env python

import os
import sys
import re
import string
import itertools

def get_value(lines, prefix):
  for l in lines:
    if l.startswith(prefix):
      return int(l[(len(prefix) + 1):].strip())

  return 0 

with open('/tmp/spec-ipa-se.csv', 'w') as output:
  ipa_icf_files = [x.strip() for x in os.popen('find /home/marxin/Programming/cpu2006 -name "*icf*" | grep wpa | grep martin-ipa-icf2 | grep lto-ipa-icf').readlines()]
  for f in ipa_icf_files:
    basename = os.path.basename(f)
    spec = basename[:basename.find('.')]
    fullspecname = f.strip().split('/')[7]

    if spec == 'sphinx_livepretend':
      spec = 'sphinx3'

    gold_icf_file = '/home/marxin/Programming/cpu2006/summary/martin-gold/gcc-O2-lto-no-ipa-icf_' + spec + '.log'

    cmd = './icf_parser.py %s %s f' % (gold_icf_file, f)
    print('Running: ' + cmd)
    print(spec)

    r = os.popen(cmd).readlines()

    for l in r:
      print(l.strip())

    values = []

    values.append(fullspecname)
    values.append(get_value(r, 'ICF TOTAL:'))
    values.append(get_value(r, 'IPA TOTAL:'))
    values.append(get_value(r, 'Intersection:'))
    values.append(get_value(r, 'Just seen by ICF:'))
    values.append(get_value(r, 'Just seen by IPA:'))

    output.write(string.join(map(lambda x: str(x), values), ':') + '\n')
