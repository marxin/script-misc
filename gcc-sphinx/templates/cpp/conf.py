# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'The C Preprocessor'
copyright = '1987-2021 Free Software Foundation, Inc.'
authors = 'Richard M. Stallman, Zachary Weinberg'

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
latex_documents = [
  ('index', 'cpp.tex', project, authors, 'manual'),
]

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('invocation', 'cpp', project, [authors], 1),
]
