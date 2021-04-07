# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'The GNU Go Compiler'
copyright = '2010-2021 Free Software Foundation, Inc.'
authors = 'Ian Lance Taylor'

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
latex_documents = [
  ('index', 'gccgo.tex', project, authors, 'manual'),
]

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('invoking-gccgo', 'gccgo', 'A GCC-based compiler for the Go language', [authors], 1),
]
