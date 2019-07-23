#!/usr/bin/env python3

import argparse
import os
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description = 'Compare plist files made by clang-static-analyzer')

parser.add_argument('directory', help = 'Path to folder with plist files')
parser.add_argument('plist', help = 'Reference plist file')
args = parser.parse_args()

seen_issues = set()

def parse_plist(path):
    file = None
    context = None
    type = None

    tree = ET.parse(path)
    root = tree.getroot()    
    nodes = [n for n in root.iter()]

    parsed_files = None
    for i, child in enumerate(nodes):
        if child.tag == 'key' and child.text == 'files':
            parsed_files = [x.text for x in nodes[i + 1]]
            break

    for i, child in enumerate(nodes):
        if child.tag == 'key':
            if child.text == 'issue_context':
                type = nodes[i - 7].text
                context = nodes[i + 1].text
                file_index = int(list(nodes[i + 5].iter('integer'))[2].text)
                yield ':'.join([parsed_files[file_index], type, context])

for root, dirs, files in os.walk(args.directory):
    for f in files:
        if f.endswith('.plist'):
            for r in parse_plist(os.path.join(root, f)):
                seen_issues.add(r)

# Read reference plist file
known_issues = set([x.strip() for x in open(args.plist).readlines()])

print('Known issues: %d, seen issues now: %d' % (len(known_issues), len(seen_issues)))
difference = list(seen_issues - known_issues)
if len(difference) > 0:
    print('New issues:')
    for d in difference:
        print(d)
