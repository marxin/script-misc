# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'The GCC Quad-Precision Math Library'
copyright = '2010-2021 Free Software Foundation, Inc.'
authors = 'GCC Developer Community'

latex_documents = [
  ('index', 'libquadmath.tex', project, authors, 'manual'),
]
