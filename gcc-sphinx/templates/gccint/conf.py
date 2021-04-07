# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'GNU Compiler Collection Internals'
copyright = '1988-2021 Free Software Foundation, Inc.'
authors = 'Richard M. Stallman and the GCC Developer Community'

latex_documents = [
  ('index', 'gccint.tex', project, authors, 'manual'),
]
