#!/usr/bin/env python3

import sys
from itertools import takewhile
from pathlib import Path

total = []

folder = Path(sys.argv[1])

for path in folder.iterdir():
    with path.open() as f:
        lines = f.read().splitlines()
        for i in range(len(lines)):
            line = lines[i]
            if line.endswith('Checked files'):
                lines = lines[i + 1:]
                checks = list(takewhile(lambda x: 'TOTAL' not in x, lines))
                for c in checks:
                    parts = c.split(']')[1].split()
                    name = parts[0]
                    duration = float(parts[1])
                    frac = float(parts[2])
                    if name not in ('rpm2cpio') and duration > 3:
                        total.append((name, duration, frac, str(path)))
                break

for name, duration, frac, path in sorted(total, key=lambda x: x[1], reverse=True):
    print(f'{path:30} {duration:5} {frac:5}% {name:30}')
