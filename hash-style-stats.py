#!/usr/bin/env python3

import subprocess
from pathlib import Path


def parse_readelf(file, stdout):
    try:
        filesize = file.stat().st_size
    except FileNotFoundError:
        return None
    hash_size = None
    gnu_hash_size = None

    lines = stdout.splitlines()
    for line in lines:
        parts = line.split()
        if '.gnu.hash' in line:
            gnu_hash_size = int(parts[6], 16)
        elif '.hash' in line:
            hash_size = int(parts[6], 16)

    if not gnu_hash_size or not hash_size:
        return None

    # print(100 * gnu_hash_size / filesize, 100 * hash_size / filesize)
    return {'filesize': filesize, 'gnu': gnu_hash_size, 'hash': hash_size}


total = {}
parsed = 0

files = list(Path('/usr/bin').iterdir()) + list(Path('/usr/lib64').iterdir())
for file in files:
    r = subprocess.run(f'readelf -SW {file}', encoding='utf8',
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    data = parse_readelf(file, r.stdout)
    if data:
        parsed += 1
        for k, v in data.items():
            value = total.setdefault(k, 0)
            total[k] += v

for k in total.keys():
    total[k] = round(total[k] / (1024 * 1024), 2)

print('SIZEs in MB:')
print(total, '.gnu.hash %:', round(100 * total['gnu'] / total['filesize'], 2),
      '.hash %:', round(100 * total['hash'] / total['filesize'], 2))
print(parsed, len(files))
