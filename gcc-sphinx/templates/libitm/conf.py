# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'The GNU Transactional Memory Library'
copyright = '2011-2021 Free Software Foundation, Inc.'
authors = 'GCC Developer Community'

latex_documents = [
  ('index', 'libitm.tex', project, authors, 'manual'),
]
