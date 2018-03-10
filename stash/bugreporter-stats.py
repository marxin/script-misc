#!/usr/bin/env python3

import requests
import json
import os

api_key = 'uJQXc9LWxiawCzsX30vDOPfwBPYGdiYVFCUCOydl'
base_url = 'https://gcc.gnu.org/bugzilla/rest.cgi/'

u = base_url + 'bug'

CHUNK = 500
output = open('/home/marxin/BIG/data-bugzilla.json', 'w')
for i in range(200):
    ids = [5000 + x + (i * CHUNK) for x in range(CHUNK)]
    r = requests.get(u, params = {'api_key': api_key, 'bug_status': ['RESOLVED', 'VERIFIED', 'CLOSED'], 'product': 'gcc', 'id': ids})
    data = r.json()
    bugs = data['bugs']
    output.write(json.dumps(bugs) + '\n')
    print('%d: %s: %d' % (ids[0], str(r), len(bugs)))

