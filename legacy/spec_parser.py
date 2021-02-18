#!/usr/bin/env python

from __future__ import print_function
import os
import sys
from glob import glob

int_tests = ['400.perlbench', '401.bzip2', '403.gcc', '429.mcf', '445.gobmk', '456.hmmer', '458.sjeng', '462.libquantum', '464.h264ref', '471.omnetpp', '473.astar', '483.xalancbmk']

testsuite = {}
sizedictionary = {}

### MAIN ###
if len(sys.argv) < 4:
	print('usage: spec_parser [rootdir] [size/time] benchmarks')
	exit(-1)

inputs = sys.argv[3:]
rootpath = sys.argv[1]

def parse_binary(test, justint):
	sizedictionary[test] = {}
	benchdir = rootpath + '/benchspec/CPU2006/'
	for b in os.listdir(benchdir):
		if justint and (b in int_tests) is False:
			continue

		if justint is False and b in int_tests:
			continue

		if os.path.isdir(os.path.join(benchdir, b)) is False:
			continue

		exefolder = os.path.join(benchdir, b, 'exe')

		if os.path.isdir(exefolder) is False:
			continue

		for f in os.listdir(exefolder):
			exefile = os.path.join(exefolder, f)
			if exefile.endswith(test):
				size = int(os.path.getsize(exefile)) 
				sizedictionary[test][b] = size
				continue

def parse_log(p):
	dictionary = {}

	f = open(p, 'r')
	lines = f.readlines()[5:]

	i = 0

	while lines[i].strip() is not '':
		l = lines[i].strip()
		parts = l.split(',')
		
		name = parts[0]
		result = parts[2]

		if (name in dictionary) is False:
			dictionary[name] = []

		dictionary[name].append(result)

		i += 1

	aggregates = {}

	for key in dictionary:
		aggregates[key] = count_average(dictionary[key])

	return aggregates

def find_log(num):
	p = os.path.join(rootpath, 'result')

	if len(num) == 2:
		num = '0' + num

	pattern = p + '/*.' + num + '*.csv'
	result = glob(pattern)[0]
	return result

def count_average(dictionary):
	sum = 0
	count = 0
	for v in dictionary:
		sum += float(v)
		count += 1

	return sum / count

def print_size_results():
	first = sizedictionary[inputs[0]]

	print('tests:', end = ''),
	for run in inputs:
		print(run + ':', end = '')
	
	print('')

	differences = {}

	for benchmark in sorted(first.keys()):
		print(benchmark + ':', end = '')
		print(str(first[benchmark]) + ':', end = '')

		for run in inputs:
			data = sizedictionary[run][benchmark]
			diff = (float(data) / first[benchmark] * 100)

			if (run in differences) is False:
				differences[run] = 0

			differences[run] += diff;

			print('%.2f:' % diff, end = '')
		print('')

	print('average:0:', end = '')
	for k in inputs:
		print('%.2f:' % (differences[k] / len(first.keys())), end = '')
	print('')

def print_results():
	first = testsuite[inputs[0]]

	print('tests:', end = ''),
	for run in inputs:		
		print(run + ':', end = '')
	
	print('')

	differences = {}

	for benchmark in sorted(first.keys()):
		print(benchmark + ':', end = '')
		print(str(first[benchmark]) + ':', end = '')

		for run in inputs:
			data = testsuite[run][benchmark]
			diff = (first[benchmark] / data * 100)

			if (run in differences) is False:
				differences[run] = 0

			differences[run] += diff;

			print('%.2f:' % diff, end = '')
		print('')

	print('average:0:', end = '')

	for k in inputs:
		print('%.2f:' % (differences[k] / len(first.keys())), end = '')
	print('')

def timereport():
	for arg in inputs:
		f = find_log(arg)
		data = parse_log(f)
		testsuite[arg] = data

	print_results()

def sizereport(justint):
	for arg in inputs:
		parse_binary(arg, justint)
	
	print_size_results()

if sys.argv[2] == 'size':
	justint = inputs[0] == 'int'
	inputs = inputs[1:]

	sizereport(justint)
else:
	timereport()
