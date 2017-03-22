#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse

from git import Repo
from itertools import *

def strip_empty_strings(lines):
    return list(reversed(list(dropwhile(lambda x: x == '', reversed(lines)))))

parser = argparse.ArgumentParser(description='Extract SVN revisions to patches.')
parser.add_argument('gitlocation', help = 'GIT repository location')
parser.add_argument('revisions', help = 'SVN revisions separated by space')
args = parser.parse_args()

os.chdir(args.gitlocation)
repo = Repo('.')

revisions = sorted(args.revisions.split(','))
assert len(revisions) == len(set(revisions))

commits = []
# find commits
log = list(repo.iter_commits('parent/master~10000..parent/master'))

for revision in revisions:
    for l in log:
        if 'trunk@' + revision in l.message:
            commits.append(l)
            continue

assert len(revisions) == len(commits)
patches = []

for i, c in enumerate(commits):
    r = subprocess.run('git format-patch -1 %s' % c.hexsha, stdout = subprocess.PIPE, shell = True)
    assert r.returncode == 0
    f = r.stdout.decode('utf-8').strip()

    # modify ChangeLog entries to patch body
    lines = [x.rstrip() for x in open(f).readlines()]
    os.remove(f)

    in_changelog = False

    changelog_lines = []
    patch_lines = []

    # skip beginning
    diff_string = 'diff --git'
    header = list(takewhile(lambda x: not x.startswith(diff_string) and not x.startswith('Subject:'), lines))    
    lines = lines[len(header):]
    lines = list(dropwhile(lambda x: not x.startswith(diff_string), lines))
    while len(lines) != 0:
        first_line = lines[0]
        lines = lines[1:]
        f = first_line.split(' ')
        assert len(f) == 4
        if f[-1].endswith('ChangeLog'):
            changelog_lines.append(f[-1][2:] + ':')
            changelog_lines.append('')
            chunk = list(takewhile(lambda x: not x.startswith(diff_string), lines))
            diff = [x[1:] for x in chunk if x.startswith('+') and not x.startswith('+++')]
            diff = strip_empty_strings(diff)
            if diff[-1].startswith('20'):
                diff = [diff[-1], ''] + diff[:-1]
            diff = strip_empty_strings(diff)

            for d in diff[1:]:
                assert not d.startswith('20')
            changelog_lines.append('\n'.join(diff) + '\n')            
        else:
            chunk = list(takewhile(lambda x: not x.startswith(diff_string), lines))
            patch_lines.append(first_line)
            patch_lines += chunk

        lines = lines[len(chunk):]

    path = '{0:04d}-patch-'.format(i + 1) + revisions[i] + '.patch'
    with open(path, 'w') as w:
        w.write('\n'.join(header) + '\n')
        w.write('Subject: Backport r' + revisions[i] + '\n\n')
        w.write('\n'.join(changelog_lines) + '\n')
        w.write('---\n')
        w.write('\n'.join(patch_lines))

    print('Generating %d/%d: %s' % (i + 1, len(revisions), path))
