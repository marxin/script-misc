# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'Using GNU Fortran'
copyright = '1999-2021 Free Software Foundation, Inc.'
authors = 'The gfortran team'

latex_documents = [
  ('index', 'gfortran.tex', project, authors, 'manual'),
]
