#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
from itertools import takewhile
from pathlib import Path

OUTPUT = 'xxd-output'


def is_not_start(line):
    return not line.startswith('00000000:')


lines = open(sys.argv[1]).read().splitlines()

filenames = list(takewhile(is_not_start, lines))
lines = lines[len(filenames):]

data = {}

while lines:
    chunk = lines[:1]
    lines = lines[1:]
    chunk += list(takewhile(is_not_start, lines))
    lines = lines[len(chunk) - 1:]
    data[filenames[0]] = '\n'.join(chunk)
    filenames = filenames[1:]

assert not filenames

shutil.rmtree(OUTPUT)
for filename, data in data.items():
    path = Path(OUTPUT, filename)
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True)

    with tempfile.NamedTemporaryFile('w', delete=False) as fp:
        fp.write(data)
        fp.close()
        subprocess.check_output(f'xxd -r {fp.name} > {path}', shell=True)
        os.unlink(fp.name)

    print(f'Saving {path}')
