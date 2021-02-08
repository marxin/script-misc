#!/usr/bin/env python3

import argparse
import concurrent.futures
import os
import shutil
import subprocess

HELP = 'Download all RPM files for a project'
parser = argparse.ArgumentParser(description=HELP)
parser.add_argument('api', help='API')
parser.add_argument('project', help='OBS project name')
parser.add_argument('output_folder',
                    help='Output folder where to the RPM files')
parser.add_argument('--jobs', '-j', type=int, default=16,
                    help='Output folder where to the RPM files')
args = parser.parse_args()

shutil.rmtree(args.output_folder, ignore_errors=True)
os.mkdir(args.output_folder)

packages = subprocess.check_output(f'osc ls -e {args.project}', shell=True,
                                   encoding='utf8').splitlines()
packages = sorted(packages)


def get_package(package):
    print(package)
    os.chdir(args.output_folder)
    cmd = f'osc getbinaries {args.project} {package} standard x86_64'
    subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)


with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as executor:
    futures = []
    for package in packages:
        futures.append(executor.submit(get_package, package))
    concurrent.futures.wait(futures)
