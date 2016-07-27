#!/usr/bin/env python3

import requests
import json
import argparse
import re

base_url = 'https://gcc.gnu.org/bugzilla/rest.cgi/'
statuses = ['UNCONFIRMED', 'ASSIGNED', 'SUSPENDED', 'NEW', 'WAITING', 'REOPENED']
search_summary = ' Regression]'
regex = '(.*\[)([0-9\./]*)( [rR]egression].*)'

def get_bugs(api_key, query):
    u = base_url + 'bug'
    r = requests.get(u, params = query)
    return r.json()['bugs']

def modify_bug(api_key, id, params, doit):
    u = base_url + 'bug/' + str(id)

    data = {
        'ids': [id],
        'api_key': api_key }

    data.update(params)

    if doit:
        r = requests.put(u, json = data)
        print(r)

def search(api_key, remove, add, limit, doit):
    # 1) get bug info to find 'cc'
    bugs = get_bugs(api_key, {'api_key': api_key, 'summary': search_summary, 'bug_status': statuses})
    count = 0
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
                modify_bug(api_key, b['id'], {'summary': new_summary}, doit)
                print()

def replace_milestone(api_key, limit, old_milestone, new_milestone, comment, doit):
    bugs = get_bugs(api_key, {'api_key': api_key, 'bug_status': statuses, 'target_milestone': old_milestone})
    count = 0

    for b in bugs:
        if count >= limit:
            return
        count += 1
        print('Changing target milestone for PR%d: %s' % (b['id'], new_milestone))
        args = {'target_milestone': new_milestone}
        if comment != None:
            args['comment'] = {'comment': comment }
        modify_bug(api_key, b['id'], args, doit)

parser = argparse.ArgumentParser(description='')
parser.add_argument('api_key', help = 'API key')
parser.add_argument('--remove', nargs = '?', help = 'Remove a release from summary')
parser.add_argument('--add', nargs = '?', help = 'Add a new release to summary, e.g. 6:7 will add 7 where 6 is included')
parser.add_argument('--limit', nargs = '?', help = 'Limit number of bugs affected by the script')
parser.add_argument('--doit', action = 'store_true', help = 'Really modify BUGs in the bugzilla')
parser.add_argument('--new-target-milestone', help = 'Set a new target milestone, e.g. 4.9.3:4.9.4 will set milestone to 4.9.4 for all PRs having milestone set to 4.9.3')
parser.add_argument('--comment', help = 'Comment a PR for which we set a new target milestore')

args = parser.parse_args()
# Python3 does not have sys.maxint
args.limit = int(args.limit) if args.limit != None else 10**10

if args.remove != None or args.add != None:
    search(args.api_key, args.remove, args.add, args.limit, args.doit)
if args.new_target_milestone != None:
    t = args.new_target_milestone.split(':')
    assert len(t) == 2
    replace_milestone(args.api_key, args.limit, t[0], t[1], args.comment, args.doit)
