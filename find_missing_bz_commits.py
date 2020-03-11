#!/usr/bin/env python3

import requests
import json
import argparse
import subprocess
import re

base_url = 'https://gcc.gnu.org/bugzilla/rest.cgi/'
pr_regex = re.compile('PR\ (.*)\/([0-9]+)')

def find_prs(message):
    for line in message.split('\n'):
        m = pr_regex.search(line)
        if m:
            yield m.group(2)

branches = ['origin/releases/gcc-8', 'origin/releases/gcc-9', 'origin/master']

commits = {}

subprocess.check_output('wget https://gcc.gnu.org/pipermail/gcc-bugs/2020-March.txt.gz -O /tmp/march.txt.gz', shell = True)
subprocess.check_output('gunzip -f /tmp/march.txt.gz', shell = True)

bugzilla_messages = open('/tmp/march.txt').readlines()
sent_comments = set()

for l in bugzilla_messages:
    l = l.rstrip()
    if l.startswith('commit r'):
        sent_comments.add(l)

for b in branches:
    r = subprocess.check_output('git log %s --since=2020-03-04 --oneline --pretty=tformat:"%%H"' % b, shell = True, encoding = 'utf')
    for hash in r.strip().split('\n'):
        commits[hash] = subprocess.check_output('git log --format=medium -n 1 ' + hash, shell = True, encoding = 'utf8').strip()

for hash, message in commits.items():
    prs = list(sorted(list(set(find_prs(message)))))
    if prs:
        for pr in prs:
            descr = subprocess.check_output('git gcc-descr --full ' + hash, shell = True, encoding = 'utf8').strip()
            needle = 'commit ' + descr
            needle2 = 'commit ' + hash
            if not needle in sent_comments and not needle2 in sent_comments:
                print('https://gcc.gnu.org/bugzilla/show_bug.cgi?id=%s' % pr)
                message_lines = message.split('\n')
                message_lines[0] = needle
                message = '\n'.join(message_lines)
                print(message)
