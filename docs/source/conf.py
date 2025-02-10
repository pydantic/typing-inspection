# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'typing-inspection'
copyright = '2025-%Y, Victorien'
author = 'Victorien'
release = '0.1.0'

SOURCE_URI = 'https://github.com/pydantic/typing-inspection/tree/main/src/%s'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx_paramlinks',
    'sphinx_toggleprompt',
]

rst_prolog = """
.. role:: python(code)
    :language: python
    :class: highlight
"""

templates_path = ['_templates']
exclude_patterns = []

add_module_names = False

autodoc_member_order = 'bysource'
autodoc_type_aliases = {
    'Qualifier': 'Qualifier',
}

extlinks = {
    'source': (SOURCE_URI, '%s'),
}


intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'typing_extensions': ('https://typing-extensions.readthedocs.io/en/latest', None),
    'tspec': ('https://typing.readthedocs.io/en/latest', None),
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']

html_theme_options = {
    'source_repository': 'https://github.com/pydantic/typing-inspection/',
    'source_branch': 'main',
    'source_directory': 'docs/source/',
}
