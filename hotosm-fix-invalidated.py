#!/usr/bin/env python3

import requests
import dateutil.parser
import argparse

parser = argparse.ArgumentParser(description='Invalidate already invalidated tasks for HOTOSM.')
parser.add_argument('project_id', help = 'ID of the project')
parser.add_argument('auth_token', help = 'Authorization header from POST request')

args = parser.parse_args()

def invalidate(id):
    headers = {'Authorization': args.auth_token}
    url = 'https://tasks.hotosm.org/api/v1/project/%s/lock-for-validation' % args.project_id

    r = requests.post(url, json = {'taskIds': [id]}, headers = headers)
    assert r.status_code == requests.codes.ok

    url = 'https://tasks.hotosm.org/api/v1/project/%s/unlock-after-validation' % args.project_id
    r = requests.post(url, json = {'validatedTasks': [{'taskId': id, 'status': 'INVALIDATED', 'comment': ''}]}, headers = headers)
    assert r.status_code == requests.codes.ok

url = 'https://tasks.hotosm.org/api/v1/project/%s' % args.project_id

r = requests.get(url)
d = r.json()

tasks = d['tasks']['features']

d = {}

tasks_to_do = []

for t in tasks:
    properties = t['properties']
    status = properties['taskStatus']
    if not status in d:
        d[status] = 0
    d[status] += 1
    id = properties['taskId']

    if status == 'MAPPED':
        tasks_to_do.append(id)

print('Statistics:')
print(d)
print('TOTAL: %d' % len(tasks))
print('Invalidating:')

for i, t in enumerate(tasks_to_do):
    td = requests.get(url + '/task/' + str(t)).json()

    actions = []
    for th in td['taskHistory']:
        actions.append({'by': th['actionBy'], 'time': dateutil.parser.parse(th['actionDate']), 'action': th['action'], 'actionText': th['actionText'], 'taskId': t})

    if len(actions) > 0:
        latest = sorted(actions, key = lambda x: x['time'], reverse = True)[0]
        if latest['actionText'] == 'INVALIDATED':
            print('%d/%d: %s' % (i, len(tasks_to_do), str(latest)))
            id = latest['taskId'] 
            invalidate(id)
