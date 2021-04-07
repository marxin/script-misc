# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'Cpplib Internals'
copyright = '2000-2021 Free Software Foundation, Inc.'
authors = 'Neil Booth'

latex_documents = [
  ('index', 'gcc.tex', project, authors, 'manual'),
]
