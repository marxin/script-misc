# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'GNU Offloading and Multi Processing Runtime Library'
copyright = '2006-2021 Free Software Foundation, Inc.'
authors = 'GCC Developer Community'

latex_documents = [
  ('index', 'libgomp.tex', project, authors, 'manual'),
]
