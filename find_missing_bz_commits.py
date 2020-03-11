#!/usr/bin/env python3

import requests
import json
import argparse
import subprocess
import re
import sys

import xmltodict

base_url = 'https://gcc.gnu.org/bugzilla/rest.cgi/'
pr_regex = re.compile('PR\ (.*)\/([0-9]+)')

def find_prs(message):
    for line in message.split('\n'):
        m = pr_regex.search(line)
        if m:
            yield m.group(2)

def get_commits_from_comments(pr):
    sys.stderr.write('... get ' + pr + '\n')
    r = requests.get('https://gcc.gnu.org/bugzilla/show_bug.cgi?id=%s&ctype=xml' % pr)
    data = xmltodict.parse(r.text)
    comments = data['bugzilla']['bug']['long_desc']
    if type(comments) == list:
        for comment in comments:
            text = comment['thetext']
            for l in text.split('\n'):
                l = l.rstrip()
                if l.startswith('commit '):
                    yield l

commits = {}
branches = ['origin/releases/gcc-8', 'origin/releases/gcc-9', 'origin/master']

for b in branches:
    r = subprocess.check_output('git log %s --since=2020-03-04 --oneline --pretty=tformat:"%%H"' % b, shell = True, encoding = 'utf')
    for hash in r.strip().split('\n'):
        commits[hash] = subprocess.check_output('git log --format=medium -n 1 ' + hash, shell = True, encoding = 'utf8').strip()

items = commits.items()
counter = 0
for hash, message in items:
    counter += 1
    sys.stderr.write('%d/%d\n' % (counter, len(items)))
    prs = list(sorted(list(set(find_prs(message)))))
    if prs:
        for pr in prs:
            descr = subprocess.check_output('git gcc-descr --full ' + hash, shell = True, encoding = 'utf8').strip()
            needle = 'commit ' + descr
            needle2 = 'commit ' + hash
            comment_commits = set(get_commits_from_comments(pr))
            if not needle in comment_commits and not needle2 in comment_commits:
                print('https://gcc.gnu.org/bugzilla/show_bug.cgi?id=%s' % pr)
                message_lines = message.split('\n')
                message_lines[0] = needle
                message = '\n'.join(message_lines)
                print(message)
