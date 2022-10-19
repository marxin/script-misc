#!/usr/bin/env python3

import sys
import argparse
import os
import glob
import shutil
import subprocess

parser = argparse.ArgumentParser(description='Bisect object files.')
parser.add_argument('action', nargs = '?', metavar = 'action', help = 'Action', choices = ['save', 'bisect'])
parser.add_argument('-s', '--source', help = 'Source directory')
parser.add_argument('-t', '--target', help = 'Target directory')
parser.add_argument('-r', '--range', help = 'In format "x,y". [X,Y] files will be copied from source directory (rest from target)')

source_backup = '/tmp/gcc.good'
target_backup = '/tmp/gcc.bad'

args = parser.parse_args()

FNULL = open(os.devnull, 'w')

def clean_folder(folder):
    shutil.rmtree(folder, ignore_errors = True)
    os.mkdir(folder)

def copy_files(source, target, files):
    for f in files:
        destination = os.path.join(target, f)
        d = os.path.dirname(destination)
        if not os.path.exists(d):
            os.makedirs(d)

        shutil.copy(os.path.join(source, f), destination)

def get_objects(folder):
    if not folder.endswith('/'):
        folder += '/'

    objects = []

    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.o'):
                f = os.path.join(root, file)
                objects.append(f)

    return sorted([x[len(folder):] for x in objects])

def copy_file(source, target):
    r = subprocess.call(f'diff {source} {target}', shell = True, stdout = FNULL)
    if r != 0:
        print(f'Copying {source} -> {target}')
        shutil.copy(source, target)

if args.action == 'save':
    if args.source == None:
        print('-s argument is required')
        exit(1)

    if args.target == None:
        print('-t argument is required')
        exit(1)

    source_objects = get_objects(args.source)
    target_objects = get_objects(args.target)

    assert(source_objects == target_objects)
    objects = source_objects

    print('Saving %d files to %s and %s folders' % (len(objects), source_backup, target_backup))

    clean_folder(source_backup)
    copy_files(args.source, source_backup, objects)

    clean_folder(target_backup)
    copy_files(args.target, target_backup, objects)

elif args.action == 'bisect':
    source_objects = get_objects(source_backup)
    if len(source_objects) == 0:
        print('No source objects found in %s' % source_backup)
        exit(1)

    target_objects = get_objects(target_backup)
    if len(target_objects) == 0:
        print('No target objects found in %s' % target_backup)
        exit(1)

    if source_objects != target_objects:
        print('Source and target objects are different!')
        exit(1)

    objects = source_objects

    print('There are %d objects files to bisect' % len(objects))

    if args.target == None:
        print('-t argument is required')
        exit(1)

    if args.range == None:
        print('-r argument is required')
        exit(1)

    tokens = args.range.split(',')
    assert len(tokens) == 2
    start = int(tokens[0])
    end = int(tokens[1])

    for i in range(len(objects)):
        f = objects[i]
        source = None
        if i >= start and i <= end:
            source = os.path.join(source_backup, f)
        else:
            source = os.path.join(target_backup, f)

        target = os.path.join(args.target, f)
        copy_file(source, target)
