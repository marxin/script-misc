#!/usr/bin/env python3

import argparse
import concurrent.futures
import subprocess
import sys
import time
from pathlib import Path

import requests

THRESHOLD = 90
SIZE_THRESHOLD = 10 * 1024 * 1024

parser = argparse.ArgumentParser(description='Check debuginfod based on system binaries')
parser.add_argument('--verbose', '-v', action='store_true', help='Verbose')
parser.add_argument('-n', type=int, default=100, help='Number of checked packages')
args = parser.parse_args()


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


def get_debuginfo(binary, buildid, verbose):
    url = f'https://debuginfod.opensuse.org/buildid/{buildid}/debuginfo'
    start = time.monotonic()
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        print(binary, url, response.status_code)
    return (binary, response, len(response.content), time.monotonic() - start)


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

failures = 0
total_size = 0

with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
    futures = []
    files = sorted(filter(is_small, buildids.items()))
    fraction = len(files) // args.n
    files = files[::fraction]
    print(f'Checking {len(files)} packages:')
    for file, buildid in files:
        futures.append(executor.submit(get_debuginfo, file, buildid, args.verbose))
    concurrent.futures.wait(futures)
    print()

    for future in futures:
        binary, response, size, duration = future.result()
        if response.status_code != 200:
            failures += 1
            print('WARNING:', binary, buildids[binary], response.status_code)
        else:
            total_size += size

    success_rate = 100.0 * (len(files) - failures) / len(files)
    print(f'Transfered {total_size // (1024 ** 2)} MB')
    print(f'Success rate: {success_rate:.2f}%, threshold: {THRESHOLD} %')
    sys.exit(1 if success_rate < THRESHOLD else 0)
