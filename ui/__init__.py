"""The web interface.

This package imports `core`; `core` never imports this one. That is the whole
architecture in one sentence: the calculation runs the same way in the browser,
in a notebook and in the test suite, because it does not know which of them is
calling.

The screen labels are in English (Documento 4, capitulo 4) while the
documentation stays in Portuguese. The table and column names were already in
English, so the screen, the data and the report speak the same language.
"""
