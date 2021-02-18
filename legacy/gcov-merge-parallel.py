#!/usr/bin/env python3

import os
import tempfile
import concurrent.futures
import subprocess
import shutil

root = '/tmp/git'
output_root = '/dev/shm/git-output'

shutil.rmtree(output_root, ignore_errors=True)
os.mkdir(output_root)

folders = [os.path.join(root, x) for x in os.listdir(root)]

def merge(folder_a, folder_b):
    tmp = tempfile.mkdtemp(dir=output_root)
    cmd = 'gcov-tool merge %s %s -o %s' % (folder_a, folder_b, tmp)
    subprocess.check_output(cmd, shell=True)
    if folder_a.startswith('/dev/shm/git-output'):
        shutil.rmtree(folder_a, ignore_errors=True)
    if folder_b.startswith('/dev/shm/git-output'):
        shutil.rmtree(folder_b, ignore_errors=True)
    return tmp

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
    while len(folders) >= 2:
        print('Processing %d folders' % len(folders), flush=True)
        futures = []
        next_folders = []
        length = len(folders)
        for i in range(int(length / 2)):
            futures.append(executor.submit(merge, folders[2 * i], folders[2 * i + 1]))
        if length % 2:
            next_folders.append(folders[-1])

        concurrent.futures.wait(futures)
        for future in futures:
            next_folders.append(future.result())
        folders = next_folders
