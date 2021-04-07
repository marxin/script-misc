# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'The GNU Go Compiler'
copyright = '2010-2021 Free Software Foundation, Inc.'
authors = 'Ian Lance Taylor'

latex_documents = [
  ('index', 'gccgo.tex', project, authors, 'manual'),
]
