"""i3ET Calculator — cradle-to-gate carbon footprint of light vehicles.

Core calculation package. This package is pure Python: it never imports the
user interface, never reads files on its own and never prints. It takes
tables in and returns tables out, so the same code runs in the web app, in a
notebook and in the test suite.

See docs/01-especificacao-funcional.md for the equations and
docs/02-dicionario-de-dados.md for the data model.
"""

__version__ = "0.1.0"
