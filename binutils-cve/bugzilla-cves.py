#!/usr/bin/env python3

import xmltodict, json, re

cve_regex = re.compile(r'CVE-[0-9]+-[0-9]+')
bintuils_bugzilla_regex = re.compile(r'https:\/\/sourceware.org\/bugzilla\/show_bug\.cgi\?id=([0-9]+)')

# the file is created from bugzilla with Export XML from all PRs assigned to matz@suse.com

data = xmltodict.parse(open('assigned.xml').read())
bugs = data['bugzilla']['bug']

# the file is created with:
# find . -name ChangeLog | xargs -L1 git diff origin/binutils-2_33-branch..origin/binutils-2_34-branch >> diff && grep '+.*PR [0-9]' diff | sed 's/.*PR //' | sort -n | uniq

mentioned_prs = set([int(l) for l in open('binutils-prs.txt').readlines()])

cve_bugs = []

for bug in bugs:
    links = set()
    comments = None
    if type(bug['long_desc']) == list:
        comments = bug['long_desc']
    else:
        comments = [bug['long_desc']]
    for comment in comments:
        text = comment['thetext']
        for link in bintuils_bugzilla_regex.findall(text):
            links.add(int(link))
    links = list(links)

    m = cve_regex.search(bug['short_desc'])
    if m:
        cve_bugs.append((int(bug['bug_id']), m.group(0), links))

cve_bugs = list(sorted(cve_bugs, key = lambda x: x[0]))

for cve in cve_bugs:
    print('%d (%s): %s' % (cve[0], cve[1], str(cve[2])))

print('Mentioned CVEs in bintuils ChangeLogs:')
for cve in cve_bugs:
    if any(map(lambda x: x in mentioned_prs, cve[2])):
        print('%d (%s): %s' % (cve[0], cve[1], str(cve[2])))
