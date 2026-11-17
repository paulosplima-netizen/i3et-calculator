"""Shared pieces of the 0.10 screens: the open project, the analysis, the header.

Every new screen (T01 to T11, T41) starts with `begin()`. It sets the page up,
finds the project file in the session, gives the file an identity if it has
none, and says whether the screen may edit. Reading and writing go through
`connect()`, which commits on exit and always turns the foreign keys on.

This module imports streamlit; `core/` does not.
"""

from __future__ import annotations

import contextlib
import sqlite3
from dataclasses import dataclass

import streamlit as st

from core import project, provenance

from . import state

OPEN_KEY = "open_projects"        # [{"path": ..., "name": ...}]
SELECTED_KEY = "selected_paths"   # caminhos marcados na T01
IDA_KEY = "ida"                   # analise corrente
SEAL_COLUMN = "Seal"


@contextlib.contextmanager
def connect(path: str | None = None):
    conn = sqlite3.connect(path or state.project_path())
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@dataclass(frozen=True)
class Context:
    path: str
    ident: dict
    mode: str                 # project.EDIT ou project.READ
    reason: str | None

    @property
    def can_edit(self) -> bool:
        return self.mode == project.EDIT


def register(path: str, name: str) -> None:
    """Remember a project in this session's list and make it the current one."""
    lista = st.session_state.setdefault(OPEN_KEY, [])
    if not any(p["path"] == path for p in lista):
        lista.append({"path": path, "name": name})
    st.session_state[SELECTED_KEY] = [path]


def selected_count() -> int:
    return max(1, len(st.session_state.get(SELECTED_KEY, [])))


def begin(title: str, *, needs_project: bool = True, edit: bool = False) -> Context | None:
    """Page header. Returns the context, or stops the page when there is no project."""
    st.set_page_config(page_title=f"{title} · i3ET Calculator", layout="wide")
    st.title(title)
    path = state.project_path()
    if not needs_project:
        return None
    if not path:
        st.info("Open or create a project on the **Home** page first.")
        st.stop()
    with connect(path) as conn:
        if project.identity(conn) is None:
            project.create(conn, state.project_name())
        ident = project.identity(conn)
        n = selected_count()
        mode = project.mode(conn, selected_count=n)
        reason = project.read_only_reason(conn, selected_count=n)
    if edit and mode == project.READ:
        st.info(reason or "This project is read-only.")
    st.caption(f"Project **{ident['ProjectName']}** · `{ident['ProjectID']}` · "
               f"{'editable' if mode == project.EDIT else 'read-only'}")
    return Context(path, ident, mode, reason)


def analyses(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute("SELECT IDA, DsA, Mode, IDVC, FuelScenario, TestNorm, IDEFV, "
                       "SPHEVEco, CombinedPowerRule, ParamProfile FROM D06_Analysis ORDER BY IDA")
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def current_ida(conn: sqlite3.Connection) -> int | None:
    rows = analyses(conn)
    ids = [r["IDA"] for r in rows]
    if not ids:
        return None
    chosen = st.session_state.get(IDA_KEY)
    return chosen if chosen in ids else ids[-1]


def pick_analysis(conn: sqlite3.Connection, *, key: str = "pick_analysis") -> int | None:
    rows = analyses(conn)
    if not rows:
        st.info("No analysis yet. Create one on **Project Configuration** (T03).")
        return None
    labels = {r["IDA"]: f"A{r['IDA']} · {r['DsA']} ({r['Mode']})" for r in rows}
    ida = st.selectbox("Analysis", list(labels), format_func=labels.get,
                       index=list(labels).index(current_ida(conn)), key=key)
    st.session_state[IDA_KEY] = ida
    return ida


def summary_phrase(conn: sqlite3.Connection, ida: int) -> str:
    """The sentence the workbook prints above its results (Control Panel title)."""
    row = conn.execute(
        "SELECT a.Mode, c.DsVC, a.FuelScenario, a.TestNorm, a.IDEFV, a.SPHEVEco "
        "FROM D06_Analysis a LEFT JOIN P29_VehicleCategory c ON c.IDVC = a.IDVC "
        "WHERE a.IDA = ?", (ida,)).fetchone()
    mode, cat, fuel, norm, efv, eco = row
    head = cat if mode == "EC" else "Free choice"
    return (f"{head} - {fuel} & Electricity - {norm} - {efv} "
            f"(SPHEV : {'Eco' if eco else 'Standard'})")


def seal_label(origin: str, run_seq: int | None) -> str:
    return provenance.label(provenance.Seal(origin), run_seq)


def seal_of(origin: str | None) -> provenance.Seal:
    if origin is None:
        return provenance.Seal(None, provenance.NOT_AVAILABLE)
    return provenance.Seal(origin)


def runs(conn: sqlite3.Connection, ida: int | None = None) -> list[dict]:
    sql = "SELECT RunID, IDA, RunSeq, FrozenAt, InputHash, Status FROM D09_Run"
    args: tuple = ()
    if ida is not None:
        sql += " WHERE IDA = ?"
        args = (ida,)
    cur = conn.execute(sql + " ORDER BY IDA, RunSeq", args)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]
