"""Camada visual: carrega o CSS e entrega blocos de HTML (docs/ferramentas, "Camada visual").

Nada aqui calcula. As telas chamam `inject()` no inicio e `blocks.*` onde querem
um bloco com a aparencia dos prototipos. Streamlit puro, sem JavaScript proprio.
"""

from __future__ import annotations

import base64
import os

import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))


def inject() -> None:
    """Injeta `theme.css` na pagina corrente."""
    with open(os.path.join(_HERE, "theme.css"), encoding="utf-8") as fh:
        st.markdown(f"<style>{fh.read()}</style>", unsafe_allow_html=True)


def asset_b64(name: str) -> str:
    with open(os.path.join(_HERE, "assets", name), "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")
