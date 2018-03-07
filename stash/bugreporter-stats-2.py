#!/usr/bin/env python3

import json
import arrow

output = open('/home/marxin/BIG/data-bugzilla.json')

bugs = []

for l in output.readlines():
    d = json.loads(l)
    bugs += d

print('TOTAL resolved/closed/verified (ID>=5000): ' + str(len(bugs)))
print()

#creation_time = arrow.get(bugs[0]['creation_time']).datetime
#print(creation_time)

creators = [x['creator'] for x in bugs]
d = {}
for c in creators:
    if c in d:
        d[c] += 1
    else:
        d[c] = 1

for c in sorted(d.items(), key = lambda x: x[1], reverse = True)[:200]:
    print('%50s: %10d' % (c[0], c[1]))
