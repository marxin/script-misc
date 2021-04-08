# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'Gcc Installation Instruction'
copyright = '1988-2021 Free Software Foundation, Inc.'
authors = 'GCC Developer Community'

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
latex_documents = [
  ('index', 'install.tex', project, authors, 'manual'),
]
