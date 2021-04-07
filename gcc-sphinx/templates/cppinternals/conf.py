# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'Cpplib Internals'
copyright = '2000-2021 Free Software Foundation, Inc.'
authors = 'Neil Booth'

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
latex_documents = [
  ('index', 'cppinternals.tex', project, authors, 'manual'),
]
