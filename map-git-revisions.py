#!/usr/bin/env python3

import os

# tags changes from
# gcc-4_7_1-release
# to
# releases/gcc-4.7.1

# branches changes from:
# gcc-9-branch
# to
# origin/releases/gcc-9

needed_branches = ['4.8', '4.9', '5', '6', '7', '8', '9']

from git import Repo

def get_revisions(repo, revision, old, seen, gittosvn, svntogit):
    print('... doing: %s (%d)' % (revision, old))
    for revision in repo.iter_commits(revision):
        svn = None
        if revision.hexsha in seen:
            continue
        seen.add(revision.hexsha)
        for l in reversed(revision.message.split('\n')):
            if old:
                if 'git-svn-id' in l:
                    l = l.replace('@', ' ').split(' ')
                    svn = int(l[2])
                    break
            else:
                if 'From-SVN' in l:
                    l = l.split(' ')
                    svn = l[1]
                    assert svn.startswith('r')
                    svn = int(svn[1:].split('.')[0])
                    break
        assert svn
        gittosvn[revision.hexsha] = svn
        svntogit[svn] = revision.hexsha

def parse_git(location, revision, old):
    repo = Repo(location)
    gittosvn = {}
    svntogit = {}
    seen = set()
    get_revisions(repo, revision, old, seen, gittosvn, svntogit)
    for br in needed_branches:
        bname = ('parent/gcc-%s-branch' % br).replace('.', '_') if old else 'origin/releases/gcc-%s' % br
        get_revisions(repo, bname, old, seen, gittosvn, svntogit)
    return (gittosvn, svntogit)

surgeon = parse_git('/tmp/gcc-reposurgeon-8', 'cutover-git', False)
mirror = parse_git('/home/marxin/Programming/gcc', '4682b0a53b364ede1263a9e88951f3e81443113e', True)

files = os.listdir('/home/marxin/DATA/gcc-binaries')
existing = set([f.split('.')[0] for f in files])

print(len(existing))
have = 0
for e in existing:
    if e in mirror[0]:
        have += 1

print(have)
print('3e7b85061947bdc7c7465743ba90734566860821' in mirror[0])
print('e9c762ec4671d77e301492e4f9e92e1d3d667188' in mirror[0])
