#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import random

N = 1000
M = 100
K = 100

def next(x):
  return random.randint(0, x)

def generate_function(i):
  print('unsigned foo_%d(unsigned x)' % i)
  print('{')

  if next(1) is 0:
    print('x += %d;' % next(1000))

  if next(1) is 0:
    print('x = x << %d;' % next(10))

  if next(1) is 0:
    print('x *= %d;' % next(30))

  if next(1) is 0:
    print('x /= %d;' % (next(5) + 1))

  if next(1) is 0:
    print('for(int i = 0; i < %d; ++i)' % next(10))
    print('x += %d * x;' % next(100))

  k = i

  while k > K:
    k = next(k)
    print('x = foo_%d(x);' % k)

  print('return x;')
  print('}')
  print('')

def generate_main(r, x):
  print('int main(int argc, char **argv)')
  print('{')
  print('unsigned x = 123456;')

  for i in sorted(random.sample(r, x)):
    print('x = foo_%d(x);' % i)

  print('return x;')
  print('}')

r = range(0, N)

for x in r:  
  generate_function(x)

generate_main(r, M)
