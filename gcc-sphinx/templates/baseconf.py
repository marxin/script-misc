# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

# The full version, including alpha/beta/rc tags

# FIXME
gcc_srcdir = '/home/marxin/Programming/gcc/gcc'

def __read_file(name):
    path = os.path.join(gcc_srcdir, name)
    if os.path.exists(path):
        return open(path).read().strip()
    else:
        return ''

gcc_BASEVER = __read_file('BASE-VER')
gcc_DEVPHASE = __read_file('DEV-PHASE')
gcc_DATESTAMP = __read_file('DATESTAMP')
gcc_REVISION = __read_file('REVISION')

# The short X.Y version.
version = gcc_BASEVER

# The full version, including alpha/beta/rc tags.
release = ('%s (%s %s%s)'
           % (gcc_BASEVER, gcc_DEVPHASE, gcc_DATESTAMP,
              (' %s' % gcc_REVISION) if gcc_REVISION else ''))


# FIXME
rst_prolog = f'''
.. |gcc_version| replace:: {gcc_BASEVER}
.. |package_version| replace:: (GCC)
.. |bugurl| replace:: https://gcc.gnu.org/bugs/
'''

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'prev_next_buttons_location': 'both'
}
