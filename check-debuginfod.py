#!/usr/bin/env python3

import concurrent.futures
import subprocess
import sys
from pathlib import Path

import requests

CHUNK = 200
THRESHOLD = 90
SIZE_THRESHOLD = 10 * 1024 * 1024


def get_buildid(binary):
    output = subprocess.check_output(f'file {binary}', encoding='utf8', shell=True).strip()
    if 'symlink' in output:
        # print('Skipping symlink: {binary}')
        return None

    needle = 'BuildID[sha1]='
    if needle not in output:
        # print(f'Missing Build ID: {binary}')
        return None

    buildid = output[output.find(needle) + len(needle):]
    buildid = buildid.split()[0][:-1]
    return (binary, buildid)


def get_debuginfo(binary, buildid):
    url = f'https://debuginfod.opensuse.org/buildid/{buildid}/debuginfo'
    response = requests.get(url)
    if response.status_code != 200:
        print('\n', binary, url, r.returncode, '\n')
    print('.', end='', flush=True)
    return (binary, response)


def is_small(item):
    return Path(item[0]).stat().st_size <= SIZE_THRESHOLD


folder = Path('/usr/bin')

print(f'Analyzing {folder} file types')
buildids = {}

files = list(folder.iterdir())
with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = []
    for file in files:
        futures.append(executor.submit(get_buildid, str(file)))
    concurrent.futures.wait(futures)
    for future in futures:
        r = future.result()
        if r:
            buildids[r[0]] = r[1]

print(f'Out of {len(files)} found {len(buildids)} with a Build ID')
print(f'Checking {CHUNK} packages:')

failures = 0

with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
    futures = []
    files = sorted(filter(is_small, buildids.items()))
    files = files[len(files) // 2:]
    files = files[:CHUNK]
    for file, buildid in files:
        futures.append(executor.submit(get_debuginfo, file, buildid))
    concurrent.futures.wait(futures)
    print()

    for future in futures:
        binary, response = future.result()
        if response.status_code != 200:
            failures += 1
            print('WARNING:', binary, buildids[binary], response.status_code)

success_rate = 100.0 * (CHUNK - failures) / CHUNK
print(f'Success rate: {success_rate:.2f}%, threshold: {THRESHOLD} %')
sys.exit(1 if success_rate < THRESHOLD else 0)
