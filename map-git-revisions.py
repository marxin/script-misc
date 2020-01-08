#!/usr/bin/env python3

from git import Repo

def parse_git(location, revision, old):
    repo = Repo(location)
    gittosvn = {}
    svntogit = {}
    for revision in repo.iter_commits(revision):
        svn = None
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
    return (gittosvn, svntogit)

surgeon = parse_git('/tmp/gcc-reposurgeon-7b', 'origin/master', False)
mirror = parse_git('/home/marxin/Programming/gcc', '4682b0a53b364ede1263a9e88951f3e81443113e', True)

for git, svn in mirror[0].items():
    if not svn in surgeon[1]:
        print('Missing: %s' % svn)
