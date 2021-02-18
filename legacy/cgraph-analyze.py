#!/usr/bin/env python3

import re

functions = {}
calls = {}
lastfn = None

def is_help_fn(name):
    return re.match('.*gimple_simplify_[0-9].*', name) != None

for i, l in enumerate(open('gimple-match.c.000i.cgraph')):
    l = l.strip()
    if l.startswith('_Z') and 'gimple_simplify_' in l:
        p = l.split(' ')[0].split('/')
        name = p[0]
        id = int(p[1])

        lastfn = id
        functions[id] = name
    elif 'Calls: ' in l and lastfn:
        for p in l.split(' '):
            p2 = p.split('/')
            try:
                v = int(p2[-1])
                if not lastfn in calls:
                    calls[lastfn] = set()
                calls[lastfn].add(v)
            except:
                pass

for id, name in functions.items():    
    if not is_help_fn(name):
        called = []
        if id in calls:
            for callee in calls[id]:
                if callee in functions:
                    x = functions[callee]
                    if not is_help_fn(x):
                        print('%s:%s' % (name, x))
                    called.append(x)

        print('%d: %s' % (len(called), name))
