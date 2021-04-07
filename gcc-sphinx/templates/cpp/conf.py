# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'The C Preprocessor'
copyright = '1987-2021 Free Software Foundation, Inc.'
authors = 'Richard M. Stallman, Zachary Weinberg'

latex_documents = [
  ('index', 'cpp.tex', project, authors, 'manual'),
]
