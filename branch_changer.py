#!/usr/bin/env python3

import requests
import json
import argparse
import re

base_url = 'https://gcc.gnu.org/bugzilla/rest.cgi/'
statuses = ['UNCONFIRMED', 'ASSIGNED', 'SUSPENDED', 'NEW', 'WAITING', 'REOPENED']
search_summary = ' Regression]'
regex = '(.*\[)([0-9\./]*)( [rR]egression].*)'

def modify_bug(api_key, id, new_summary):
    u = base_url + 'bug/' + str(id)

    data = {
        'summary': new_summary,
        'ids': [id],
        'api_key': api_key }

    print(data)

"""
    r = requests.put(u, json = data)
    print(r)
"""

def search(api_key, remove, add, limit):
    # 1) get bug info to find 'cc'
    u = base_url + 'bug'
    r = requests.get(u, params = {'api_key': api_key, 'summary': search_summary, 'bug_status': statuses})
    bugs = r.json()['bugs']
    count = 0
    # Python3 does not have sys.maxint
    limit = int(limit) if limit != None else 10**10
    for b in bugs:        
        summary = b['summary']
        m = re.match(regex, summary)
        if m != None:
            versions = m.group(2).split('/')
            if remove != None:
                versions = list(filter(lambda x: x != remove, versions))
            if add != None:
                parts = add.split(':')
                assert len(parts) == 2
                for i, v in enumerate(versions):
                    if v == parts[0]:
                        versions.insert(i + 1, parts[1])
                        break

            new_version = '/'.join(versions)
            new_summary = m.group(1) + new_version + m.group(3)
            if new_summary != summary:
                if count >= limit:
                    continue
                count += 1

                print('Changing summary for PR%d:' % b['id'])
                print(summary)
                print(new_summary)
                modify_bug(api_key, b['id'], new_summary)
                print()

parser = argparse.ArgumentParser(description='')
parser.add_argument('api_key', help = 'API key')
parser.add_argument('--remove', nargs = '?', help = 'Remove a release from summary')
parser.add_argument('--add', nargs = '?', help = 'Add a new release to summary, e.g. 6:7 will add 7 when 6 is included')
parser.add_argument('--limit', nargs = '?', help = 'Limit number of bugs affected by the script')

args = parser.parse_args()
search(args.api_key, args.remove, args.add, args.limit)
