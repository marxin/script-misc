#!/usr/bin/env python

import os
import subprocess

binaries = ['./tramp_no_icf.exe', './tramp_icf.exe']
arguments = '--cartvis 1.0 0.0 --rhomin 1e-8 -n 20'
results = [[], []]

def geomean(values):
	return reduce(lambda x, y: x * y, values, 1) ** (1.0 / len(values))

def avg(values):
	return sum(values) / len(values)

for i in range(200):
	for j, b in enumerate(binaries):
		ps = subprocess.Popen(b + ' ' + arguments, stdout = subprocess.PIPE, shell = True)
		output = subprocess.check_output(['grep', 'Time'], stdin = ps.stdout)
		ps.wait()

		v = float(output.strip().split(' ')[-1])
		results[j].append(v)

	print('After %u iterations geomean:(%f)%%' % (i, 100 * (1 - geomean(results[1]) / geomean(results[0]))))
	print('After %u iterations average:(%f)%%' % (i, 100 * (1 - avg(results[1]) / avg(results[0]))))
	for j, b in enumerate(binaries):
		print('%s:%f' % (binaries[j], geomean(results[j])))
