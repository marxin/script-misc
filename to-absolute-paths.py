#!/usr/bin/env python3

import sys
from pathlib import Path

parts = sys.argv[1].split(' ')
for part in parts:
    print(Path(part).resolve())