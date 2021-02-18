#!/usr/bin/env python3

import sys

switches = []

for l in open(sys.argv[1]):
    t = 'case clusters:'

    i = l.find(t)
    if i != -1:
        l = l[i + len(t):].strip()
        parts = l.split(' ')
        switches.append(parts)

total = len(switches)
print('Total: %d' % total)

just_jump = len([s for s in switches if len(s) == 1 and s[0].startswith('JT')])
print('Just JT: %d (%.2f%%)' % (just_jump, 100.0 * just_jump / total))

just_bt = len([s for s in switches if len(s) == 1 and s[0].startswith('BT')])
print('Just BT: %d (%.2f%%)' % (just_bt, 100.0 * just_bt / total))

more = [s for s in switches if len(s) > 1]
print('Multiple: %d (%.2f%%)' % (len(more), 100.0 * len(more) / total))

with_jt = [s for s in switches if any(map(lambda x: 'JT' in x, s))]
print('Multiple with a JT: %d (%.2f%%)' % (len(with_jt), 100.0 * len(with_jt) / total))

with_bt = [s for s in switches if any(map(lambda x: 'BT' in x, s))]
print('Multiple with a BT: %d (%.2f%%)' % (len(with_bt), 100.0 * len(with_bt) / total))

s = 0

for x in more:
    s += len(x)

print('Average len with more: %.2f' % (1.0 * s / len(more)))

for m in sorted(more, key = lambda x: len(x), reverse = True)[:50]:
    print(m)

new = 0
for m in more:
    for p in m:
        if p.startswith('JT'):
            r = p[p.index(':') + 1:]
            i = r[1:].find('-') + 1
            parts = [r[:i], r[i + 1:]]
            assert len(parts) == 2
            maximum = int(parts[1])
            minimum = int(parts[0])
            assert minimum < maximum
            new += maximum - minimum + 1


print()
print('New JT range: %d, which is about ~%d B' % (new, 8 * new))
