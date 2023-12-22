# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'MicroGridsPy'
copyright = '2021, SESAM Polimi'
author = 'SESAM Polimi'

release = '0.1'
version = '0.1.0'

# -- General configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.imgconverter",
    "sphinxcontrib.images"
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    "repository_url": "https://github.com/SESAM-Polimi/MicroGridsPy-SESAM",
    "use_repository_button": True,
    "show_navbar_depth": 1,
}

html_static_path = ['_static']
html_css_files = [
    'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css',
    'css/custom.css',
]

# -- Options for EPUB output
epub_show_urls = 'footnote'

# Add custom JavaScript
html_js_files = [
    'https://code.jquery.com/jquery-3.3.1.slim.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js',
    'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js',
]


