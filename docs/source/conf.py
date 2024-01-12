# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'MicroGridsPy'
copyright = '2024, SESAM Polimi'
author = 'SESAM Polimi'

release = '2.0'
version = '2.0'

# -- General configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.imgconverter",
    "sphinxcontrib.images",
    "sphinx_togglebutton",
    "sphinx_panels",
    "sphinx_sitemap"
]

# autosummary_generate = True

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

html_baseurl = 'https://mgpy-docs.readthedocs.io/en/latest/'

html_extra_path = ['robots.txt']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    'canonical_url': 'https://mgpy-docs.readthedocs.io/en/latest/',
    'display_version': True,  # Whether to show the documentation version
    'prev_next_buttons_location': 'bottom',  # Location of the Next and Previous buttons (bottom, top, both, or None)
    'style_external_links': False,  # Whether to add an icon next to external links
    'vcs_pageview_mode': 'blob',  # Changes how view/edit links are generated (blob or edit)
    # Toc options
    'collapse_navigation': True,  # Whether to collapse the navigation entries
    'sticky_navigation': True,  # Whether to make the sidebar stick to the top of the screen
    'navigation_depth': 2,  # Maximum depth of the table of contents tree
    'includehidden': True,  # Shows hidden table of contents entries
    'titles_only': False,  # Only display the titles of documents in the navigation bar
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


