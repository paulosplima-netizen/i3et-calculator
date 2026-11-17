"""T07 · Equations & glossary — the specification, and the screen-label glossary."""

from __future__ import annotations

import os

import streamlit as st

from ui import flow, state

flow.begin("Equations & glossary", needs_project=False)
tab1, tab2 = st.tabs(["Glossary", "Equations (Document 1)"])
for tab, name in ((tab1, "glossario.md"), (tab2, "01-especificacao-funcional.md")):
    with tab:
        path = os.path.join(state.REPO, "docs", name)
        if os.path.exists(path):
            st.markdown(open(path, encoding="utf-8").read())
        else:
            st.info(f"{name} is not bundled with this installation.")
