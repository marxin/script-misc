#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import termcolor

messages = [
"64bit-portability-issue",
"strict-aliasing-punning",
"no-return-in-nonvoid-function",
"missing-sentinel",
"bufferoverflow",
"destbufferoverflow",
"memset-with-zero-length",
"missing-arg-for-fmt-string",
"implicit-fortify-decl",
"format-security",
"unchecked-return-value",
"mathmeaning",
#"no-rpm-opt-flags",
"sequence-point",
"bufferoverflowstrncat",
"stringcompare",
"uninitialized-variable",
"voidreturn",
"arraysubscript",
"implicit-pointer-decl",
]

parser = argparse.ArgumentParser(description = 'Analyze OBS log files')
parser.add_argument('location', help = 'Folder with logs')
args = parser.parse_args()

d = {}
for m in messages:
    d[m] = 0

def print_check_messages(lines):
    for l in lines:
        for m in messages:
            if m in l and ('E: ' in l or 'W: ' in l):
                d[m] += 1
                print(l)

for root, dirs, files in os.walk(args.location):
    for f in files:
        lines = [x.strip() for x in open(os.path.join(root, f)).readlines()]
        print_check_messages(lines)

print('Warning summary:')
for k, v in sorted(d.items(), key = lambda x: x[1], reverse = True):
    print('%32s: %d' % (k, v))
