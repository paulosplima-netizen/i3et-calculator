"""Acesso do usuario master as telas de dados de mercado (T39, T40, T42).

As tabelas do PBEV, da FENABRAVE e da ANFAVEA so sao mostradas ao master (decisao de
21/11/2026, docs/11). O papel vem da conta (T01, core/accounts.py); sem Master a tela explica isso.
Importa Streamlit; `core/` nao.
"""

from __future__ import annotations

import streamlit as st

from . import auth, state


def require_master(title: str) -> None:
    """Para a pagina se quem entrou nao tiver o papel Master (T01: e-mail e senha)."""
    if auth.is_master():
        st.caption("Master mode. The tables on this screen are visible to the master user only.")
        return
    auth.require_master_message(title)
    st.stop()


def reference_conn():
    """Conexao somente leitura com a base de referencia."""
    import sqlite3
    conn = sqlite3.connect(f"file:{state.reference_db_path()}?mode=ro", uri=True)
    return conn


def reference_write_conn():
    """Conexao de escrita com a base de referencia (so o master grava edicoes importadas).

    No Streamlit Cloud o disco e efemero: a gravacao vale no computador do master e chega
    aos demais usuarios pelo commit da base no repositorio (decisao 5, 22/11/2026)."""
    import sqlite3
    conn = sqlite3.connect(state.reference_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
