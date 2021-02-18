#!/usr/bin/env python3

import re
import scc

graph = {}
last_node = None

names = {}
names_back = []
def get_node_index(name):
    if name in names:
        return names[name]
    v = len(names.keys())
    names[name] = v
    names_back.append(name)
    return v

for l in open('gimple-simplify-callgraph.txt').readlines():
    l = l.rstrip()
    if l.startswith('gimple_simplify'):
        name = l.split(' ')[0]
        last_node = get_node_index(name)
        graph[last_node] = []
    else:
        assert last_node != None
        m = re.search('(gimple_simplify_[0-9]*)', l)
        if m != None:
            caller = get_node_index(m.group(1))
            if not caller in graph:
                graph[caller] = []
            graph[caller].append(last_node)
            graph[last_node].append(caller)

results = []
for component in scc.strongly_connected_components_iterative(names.values(), graph):
    fnnames = sorted([names_back[x] for x in component], reverse = True)
    results.append(fnnames)

print(len(names_back))
for r in sorted(results, key = lambda x: len(x)):
    print(r)
