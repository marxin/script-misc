#!/usr/bin/env python3

import argparse
import subprocess
import os
import tempfile

parser = argparse.ArgumentParser(description='Simple jobserver using FIFO')
parser.add_argument('jobs', type=int, help='Number of jobs')
parser.add_argument('command', help='Command to be run')
args = parser.parse_args()

with tempfile.TemporaryDirectory() as folder:
    fifopath = os.path.join(folder, 'jobserver')
    os.mkfifo(fifopath)
    writefd = os.open(fifopath, os.O_RDWR)
    written = os.write(writefd, b'+' * (args.jobs - 1))
    assert written == args.jobs - 1

    os.environ['MAKEFLAGS'] = f'--jobserver-auth=fifo:{fifopath}'
    subprocess.run(args.command, shell=True)

    readfd = os.open(fifopath, os.O_RDONLY | os.O_NONBLOCK)
    read = os.read(readfd, args.jobs)
    os.close(readfd)
    os.close(writefd)

    if len(read) != args.jobs - 1:
        print(f'WARNING: expected {args.jobs - 1} tokens, got {len(read)}')
