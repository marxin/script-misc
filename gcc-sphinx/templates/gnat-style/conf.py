# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'GNAT Coding Style: A Guide for GNAT Developers'
copyright = '1992-2021 AdaCore'
authors = 'Ada Core Technologies, Inc.'

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
latex_documents = [
  ('index', 'gnat-style.tex', project, authors, 'manual'),
]
