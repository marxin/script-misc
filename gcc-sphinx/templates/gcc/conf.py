# Configuration file for the Sphinx documentation builder.

import sys
sys.path.append('..')

from baseconf import *

project = 'Using the GNU Compiler Collection'
copyright = '1988-2021 Free Software Foundation, Inc.'

latex_documents = [
  ('index', 'gcc.tex', project,
   'Richard M. Stallman and the GCC Developer Community', 'manual'),
]
