#!/usr/bin/env python3

import argparse
import concurrent.futures
import time

import requests

ATTEMPTS = 10


def get_debuginfo(binary, buildid):
    url = f'{args.URL}/buildid/{buildid}/debuginfo'

    for i in range(ATTEMPTS):
        response = requests.get(url)
        if response.status_code != 200 or i != 0:
            print(f'Attemp #{i}', binary, buildid, response)
            time.sleep(1)
        if response.status_code == 200:
            return


parser = argparse.ArgumentParser(description='debuginfod stress test')
parser.add_argument('FILE', help='Input file with checked binaries')
parser.add_argument('URL', help='Server url')
parser.add_argument('--workers', type=int, default=8, help='Number of threads')
args = parser.parse_args()

lines = open(args.FILE).read().strip().splitlines()
print(f'Running stress test of {len(lines)} binaries in {args.workers} threads:')

with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
    futures = []
    for buildid, binary in [x.split() for x in lines]:
        futures.append(executor.submit(get_debuginfo, binary, buildid))
    concurrent.futures.wait(futures)
    for future in futures:
        future.result()
