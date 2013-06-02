#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import random

N = 50
M = N / 8
K = N / 10
C = 2000

random.seed(123456789)

def next(x):
  return random.randint(0, x)

def generate_random_command():
  k = next(5)

  if k == 0:
    print('x += %d;' % next(1000))
  elif k == 1:
    print('x = x << %d;' % next(10))
  elif k == 2:
    print('x *= %d;' % next(30))
  elif k == 3:
    print('x /= %d;' % (next(5) + 1))
  else:
    print('for(i = 0; i < %d; ++i)' % next(10))
    print('x += %d * x;' % next(100))

def generate_function(i):
  print('unsigned foo_%d(unsigned x)' % i)
  print('{')
  print('int i;')
  print('puts("%d");' % i)

  k = i

  while k > K:
    k = next(k - 1)
    for i in range(0, next(2)):
      print('x = foo_%d(x);' % k)

  for x in range(0, C):
    generate_random_command()

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

print('#include <stdio.h>')
for x in r:  
  generate_function(x)

generate_main(r, M)
