#!/usr/bin/env python

from __future__ import print_function
from sets import Set

import os
import sys
import re

if len(sys.argv) < 3:
  print('usage: icf_parse icf_dump_file ipa_dump_file')
  exit(-1)

flags = ''

if len(sys.argv) >= 4:
  flags = sys.argv[3]

def print_in_set_suffix(f):
  if f in intersection:
    print(' [IPA]')
  else:
    print()

# IPA SEM EQUALITY PARSING
ipa_set = Set()
ipa_lines = []

all_lines = open(sys.argv[2], 'r').readlines()
ipa_prefix = 'Assembler function names:'
pf_prefix = 'Parsed function:'

ipa_seen_functions = Set([x[len(pf_prefix):].strip() for x in all_lines if x.startswith(pf_prefix)])
ipa_lines = [x[len(ipa_prefix):].strip() for x in all_lines if x.startswith(ipa_prefix)]

for line in ipa_lines:
  tokens = line.split('->')
  source = tokens[1].strip()
  target = tokens[0].strip()

  ipa_set.add(source)
  ipa_set.add(target)

# ICF PARSING
text_prefix = '.text.'
icf_set = Set()

icf_lines = [x for x in open(sys.argv[1], 'r').readlines() if re.match('.*\'.text.*\'.*', x) != None]

merged_to_dictionary = {}

icf_count = 0
for merge in icf_lines:
  tokens = merge.split('\'')

  source_func = tokens[1]
  source_file = tokens[3]
  target_func = tokens[5]
  target_file = tokens[7]

  if target_func == '.text':
    continue

  source_func = source_func[len(text_prefix):]
  target_func = target_func[len(text_prefix):]

  if not source_func in ipa_set and not target_func in ipa_set:
    continue

  icf_count += 1

  icf_set.add(source_func)
  icf_set.add(target_func)

  source = (source_func, '')
  target = (target_func, '')

  if target in merged_to_dictionary:
    if not source in merged_to_dictionary[target]:
      merged_to_dictionary[target].append(source)
  else:
    merged_to_dictionary[target] = [source]

sorted_keys = sorted(merged_to_dictionary.keys(), key = lambda x: len(merged_to_dictionary[x]), reverse = True)


print ("===ICF REPORT===")
intersection = icf_set & ipa_set
just_in_icf = icf_set - intersection
just_in_ipa = ipa_set - intersection

for k in sorted_keys: 
  missing_items = [x[0] for x in merged_to_dictionary[k] if x[0] not in intersection]

  

  if 'f' in flags and len(missing_items) == 0:
    continue

  print('%4u/%-4u%s\t [%s]' % (len(merged_to_dictionary[k]), len(missing_items), k[0], k[1]), end = '')

  print_in_set_suffix(k[0])

  for alias in merged_to_dictionary[k]:
    if 'f' not in flags or alias[0] not in intersection: # f == filter
      print('          %s\t [%s]' % (alias[0], ''), end = '')
      print_in_set_suffix(alias[0])

ipa_count = len(ipa_lines)

print('\nICF TOTAL: %u in %u groups' % (icf_count, len(sorted_keys)))
print('IPA TOTAL: %u that is %.2f%%\n' % (ipa_count, 100.0 * ipa_count / icf_count))

print('Intersection: ' + str(len(intersection)))
print('Just seen by ICF: ' + str(len(just_in_icf)))
print('Just seen by IPA: ' + str(len(just_in_ipa)))

# print(just_in_ipa)
# print(ipa_lines[0])
ipa_new = [x for x in ipa_lines if x[0] in just_in_ipa or x[1] in just_in_ipa]

# for i in ipa_new:
#  print('IPA sem equality: %s\t%s' % (i[0], i[1]))
