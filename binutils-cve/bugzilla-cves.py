#!/usr/bin/env python3

import xmltodict, json, re

cve_regex = re.compile(r'CVE-[0-9]+-[0-9]+')
binutils_bugzilla_regex = re.compile(r'https:\/\/sourceware.org\/bugzilla\/show_bug\.cgi\?id=([0-9]+)')
binutils_bugzilla_prefix = 'https://sourceware.org/bugzilla/show_bug.cgi?id='
opensuse_bugzilla_prefix = 'https://bugzilla.opensuse.org/show_bug.cgi?id='
pr_regex = re.compile(r'\+\s+PR ([\w-]+\/)?([0-9]+)')

# the file is created from bugzilla with Export XML from all PRs assigned to matz@suse.com

data = xmltodict.parse(open('assigned.xml').read())
bugs = data['bugzilla']['bug']

# the file is created with:
# rm diff
# find . -name ChangeLog | xargs -L1 git diff origin/binutils-2_33-branch..origin/binutils-2_34-branch >> diff
# find . -name ChangeLog-[0-9]* | xargs -L1 git diff origin/binutils-2_33-branch..origin/binutils-2_34-branch >> diff

mentioned_prs = set()
for line in open('binutils.diff').readlines():
    line = line.strip()
    m = pr_regex.search(line)
    if m:
        mentioned_prs.add(int(m.group(2)))

# parse already mentioned CVEs in bintuils package
resolved_cves = set()

for line in open('/home/marxin/BIG/osc/home:marxin:branches:devel:gcc-clean/binutils/binutils.changes').readlines():
    line = line.strip()
    m = cve_regex.search(line)
    if m:
        resolved_cves.add(m.group(0))

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
        for link in binutils_bugzilla_regex.findall(text):
            links.add(int(link))
    links = list(links)

    m = cve_regex.search(bug['short_desc'])
    if m:
        cve_bugs.append((int(bug['bug_id']), m.group(0), links))

cve_bugs = list(sorted(cve_bugs, key = lambda x: x[0]))

print('Already mentioned in bintuils.changes: %d' % len(resolved_cves))
print('Total CVEs in openSUSE bugzilla: %d' % len(cve_bugs))

cve_bugs = [cve for cve in cve_bugs if not cve[1] in resolved_cves]

print('Not mentioned CVEs: %d' % len(cve_bugs))
for cve in cve_bugs:
    print('%d (%s): %s' % (cve[0], cve[1], str(cve[2])))

print('\nMentioned CVEs in the latest binutils release:')
for cve in cve_bugs:
    if any(map(lambda x: x in mentioned_prs, cve[2])):
        print('bnc#%d aka %s aka %s     %s%d' % (cve[0], cve[1], ' '.join(['PR' + str(x) for x in cve[2]]), opensuse_bugzilla_prefix, cve[0]))
        for b in cve[2]:
            print('  %s%d' % (binutils_bugzilla_prefix, b))
