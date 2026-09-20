"""The project file, and what the app keeps between clicks.

A project is one SQLite file: the reference parameters plus the user's own
vehicles, scenarios and emission factor versions. Creating a project copies the
reference base, which is what makes the reference immutable in practice -- the
user edits their copy, never the original.

Streamlit reruns the whole script on every interaction, so anything that must
survive a click lives in `st.session_state`, and anything expensive is cached
against the file's modification time.
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import sqlite3
import tempfile

import pandas as pd
import streamlit as st

from core import calc, loader, report, validate
from core.log import Log

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DB = os.path.join(REPO, "data", "base_referencia.sqlite")

PROJECT_KEY = "project_path"
NAME_KEY = "project_name"


def reference_exists() -> bool:
    return os.path.exists(REFERENCE_DB)


def project_path() -> str | None:
    return st.session_state.get(PROJECT_KEY)


def project_name() -> str:
    return st.session_state.get(NAME_KEY) or "sem nome"


def new_project(name: str) -> str:
    """A fresh copy of the reference base, which the user then edits."""
    destino = os.path.join(tempfile.mkdtemp(prefix="i3et_"), f"{_slug(name)}.sqlite")
    shutil.copyfile(REFERENCE_DB, destino)
    _remember(destino, name)
    return destino


def open_uploaded(arquivo, name: str | None = None) -> str:
    """Take an uploaded `.sqlite` and make it this session's project."""
    destino = os.path.join(tempfile.mkdtemp(prefix="i3et_"), arquivo.name)
    with open(destino, "wb") as fh:
        fh.write(arquivo.getbuffer())
    _check_openable(destino)
    _remember(destino, name or os.path.splitext(arquivo.name)[0])
    return destino


def close_project() -> None:
    for chave in (PROJECT_KEY, NAME_KEY):
        st.session_state.pop(chave, None)
    load_base.clear()
    run.clear()


def _remember(caminho: str, nome: str) -> None:
    st.session_state[PROJECT_KEY] = caminho
    st.session_state[NAME_KEY] = nome
    load_base.clear()
    run.clear()


def _slug(nome: str) -> str:
    limpo = "".join(c if c.isalnum() or c in "-_" else "_" for c in nome.strip())
    return limpo or f"projeto_{dt.date.today():%Y%m%d}"


def _check_openable(caminho: str) -> None:
    """Fail loudly at the door rather than three screens later."""
    conn = sqlite3.connect(caminho)
    try:
        tabelas = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    faltando = [t for t in ("P06_MassEstimationParam", "D01_Vehicle",
                            "D02_EvaluationAlternative") if t not in tabelas]
    if faltando:
        raise ValueError(
            "Este arquivo não parece um projeto da calculadora: faltam as "
            f"tabelas {', '.join(faltando)}.")


# --- leitura e calculo, memorizados contra a data de modificacao -----------

def _stamp(caminho: str) -> float:
    return os.path.getmtime(caminho) if os.path.exists(caminho) else 0.0


@st.cache_data(show_spinner=False)
def load_base(caminho: str, _stamp_value: float):
    return loader.load_sqlite(caminho)


@st.cache_data(show_spinner="Recalculando…")
def run(caminho: str, _stamp_value: float):
    """Recalculate everything from D, and validate. Never a cache of results.

    The cache key is the file and its modification time, so any edit the user
    makes invalidates it: what the screen shows is always the current state of
    the data, which is the same promise the export makes.
    """
    base = loader.load_sqlite(caminho)
    log = Log()
    validate.check_base(base, log)
    resultados = calc.calculate(base, log=log)
    for (idv, idea), r in resultados.items():
        validate.check_result(r, log, context=f"IDV {idv} / IDEA {idea}")
    return base, resultados, log


def current():
    """(base, resultados, log) for the open project, or None."""
    caminho = project_path()
    if not caminho:
        return None
    return run(caminho, _stamp(caminho))


def current_base():
    caminho = project_path()
    if not caminho:
        return None
    return load_base(caminho, _stamp(caminho))


def tables(base, resultados, log) -> dict[str, pd.DataFrame]:
    return report.build(base, resultados, log=log)


# --- escrita ---------------------------------------------------------------

def write_table(nome: str, df: pd.DataFrame) -> None:
    """Replace a whole D table in the project file.

    Only the scenario tables are ever written. The parameter tables are the
    reference, and the app has no path that touches them.
    """
    if not nome.startswith("D"):
        raise ValueError(f"{nome} nao e uma tabela de cenario")
    caminho = project_path()
    if not caminho:
        raise RuntimeError("nenhum projeto aberto")
    conn = sqlite3.connect(caminho)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        # A tabela e substituida inteira, e apagar as linhas de uma tabela pai
        # rompe momentaneamente as chaves estrangeiras das filhas. Adiar a
        # verificacao para o commit mantem o banco integro no fim -- que e o
        # que importa -- sem exigir que a tela saiba a ordem de dependencia.
        conn.execute("BEGIN")
        conn.execute("PRAGMA defer_foreign_keys = ON")
        tabela = _full(conn, nome)
        conn.execute(f"DELETE FROM {tabela}")
        df.to_sql(tabela, conn, if_exists="append", index=False)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    load_base.clear()
    run.clear()


def _full(conn, prefixo: str) -> str:
    nomes = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    for n in nomes:
        if n.split("_")[0] == prefixo:
            return n
    raise KeyError(prefixo)
