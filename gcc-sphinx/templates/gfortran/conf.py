# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'Using GNU Fortran'
copyright = '1999-2021 Free Software Foundation, Inc.'
authors = 'The gfortran team'

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
latex_documents = [
  ('index', 'gfortran.tex', project, authors, 'manual'),
]
