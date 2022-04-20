#!/usr/bin/env python3

import concurrent.futures
import subprocess
import xml.etree.ElementTree as ET

PROJECT = 'openSUSE:Factory'
THRESHOLD = 1000

out = subprocess.check_output(f'osc ls {PROJECT}', shell=True, encoding='utf8').strip()
packages = out.splitlines()
python_packages = [p for p in packages if 'python' in p]


def get_time(pkg):
    data = subprocess.check_output(f'osc api /build/{PROJECT}/standard/x86_64/{pkg}/_statistics',
                                   shell=True, encoding='utf8', stderr=subprocess.DEVNULL)
    xml = ET.fromstring(data)
    return int(xml.find('*/total/time').text)


with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = {executor.submit(get_time, x): x for x in python_packages}
    for future in concurrent.futures.as_completed(futures):
        if future.exception():
            print(f'.. skipping {futures[future]}')
        else:
            time = future.result()
            pkg = futures[future]
            if time >= THRESHOLD:
                print(pkg, time)
