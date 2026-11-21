"""Acesso do usuario master as telas de dados de mercado (T39, T40, T42).

As tabelas do PBEV, da FENABRAVE e da ANFAVEA so sao mostradas ao master (decisao de
21/11/2026, docs/11). Sem senha configurada ninguem e master e a tela explica isso.
Importa Streamlit; `core/` nao.
"""

from __future__ import annotations

import streamlit as st

from core import param_review as pr

from . import state


def require_master(title: str) -> None:
    """Para a pagina se o usuario nao for master. Mostra o campo de senha quando ha senha."""
    esperada = state.master_password()
    if st.session_state.get("master_ok") and esperada:
        st.caption("Master mode. The tables on this screen are visible to the master user only.")
        return
    if not esperada:
        st.info(f"{title} is available to the master user only, and no master password is "
                "configured in this installation.")
        st.stop()
    st.info(f"{title} is available to the master user only.")
    senha = st.text_input("Master password", type="password", key="master_pwd")
    if senha and pr.verify_master(senha, esperada):
        st.session_state["master_ok"] = True
        st.rerun()
    elif senha:
        st.error("Wrong password.")
    st.stop()


def reference_conn():
    """Conexao somente leitura com a base de referencia."""
    import sqlite3
    conn = sqlite3.connect(f"file:{state.reference_db_path()}?mode=ro", uri=True)
    return conn
