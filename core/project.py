"""Projeto: identidade, edicao ou leitura, Save as (Fase A, passo 4).

O projeto e um arquivo SQLite que o usuario baixa e reabre. `M03_Project` tem no
maximo uma linha. A base de referencia nao e um projeto e nao tem linha.

Blocos:
    PJ1  identidade
    PJ2  Save as
    PJ3  edicao ou leitura

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import sqlite3

from . import schema

EDIT = "edit"
READ = "read"


# --------------------------------------------------------------------------
# BLOCO PJ1 -- identidade
#   Le      : M03_Project.
#   Devolve : dict com a linha, ou None quando o arquivo nao e um projeto.
# --------------------------------------------------------------------------
def identity(conn: sqlite3.Connection) -> dict | None:
    cur = conn.execute("SELECT ProjectID, ProjectName, Domain, OwnerLabel, CreatedAt, "
                       "CopiedFromProjectID, SchemaVersion, IsExample FROM M03_Project")
    row = cur.fetchone()
    if row is None:
        return None
    return dict(zip([d[0] for d in cur.description], row))


def create(conn: sqlite3.Connection, name: str, owner_label: str | None = None) -> str:
    """Da identidade a um arquivo ja migrado. Devolve o ProjectID."""
    if not name or not name.strip():
        raise ValueError("project name must not be empty")
    schema.migrate(conn, project_name=name)
    if owner_label:
        conn.execute("UPDATE M03_Project SET OwnerLabel = ?", (owner_label.strip(),))
        conn.commit()
    return identity(conn)["ProjectID"]


# --------------------------------------------------------------------------
# BLOCO PJ3 -- edicao ou leitura
#   Projeto proprio: edicao. Projeto de exemplo: leitura. Dois ou mais projetos
#   selecionados na T01: todos em leitura (serve a comparacao na T06).
# --------------------------------------------------------------------------
def mode(conn: sqlite3.Connection, *, selected_count: int = 1) -> str:
    ident = identity(conn)
    if ident is None:
        raise ValueError("this file is not a project (M03_Project is empty)")
    if selected_count >= 2 or ident["IsExample"]:
        return READ
    return EDIT


def read_only_reason(conn: sqlite3.Connection, *, selected_count: int = 1) -> str | None:
    """Texto da linha de aviso (`st.info`) em modo de leitura; None em edicao."""
    ident = identity(conn)
    if ident is None:
        return None
    if selected_count >= 2:
        return "Several projects are selected: all are read-only. Select one to edit it."
    if ident["IsExample"]:
        return ("This is the Excel model (master) and cannot be edited. "
                "Use Save as to get an editable copy.")
    return None


# --------------------------------------------------------------------------
# BLOCO PJ2 -- Save as
#   Copia o arquivo por inteiro (sqlite3 backup) e da a copia um ProjectID novo,
#   `CopiedFromProjectID` preenchido e IsExample = 0.
#   Devolve : ProjectID da copia.
# --------------------------------------------------------------------------
def save_as(conn: sqlite3.Connection, dest_path: str, name: str | None = None) -> str:
    src = identity(conn)
    if src is None:
        raise ValueError("this file is not a project (M03_Project is empty)")
    dest = sqlite3.connect(dest_path)
    try:
        conn.backup(dest)
        new_id = schema.new_project_id()
        dest.execute(
            "UPDATE M03_Project SET ProjectID = ?, ProjectName = ?, CopiedFromProjectID = ?, "
            "IsExample = 0", (new_id, (name or src["ProjectName"]).strip(), src["ProjectID"]))
        dest.commit()
    finally:
        dest.close()
    return new_id


# --------------------------------------------------------------------------
# BLOCO PJ4 -- renomear e resumir
#   rename  : muda M03_Project.ProjectName (nome vazio e recusado); o ProjectID
#             nao muda.
#   summary : identidade mais o modo (EC, FC) da ultima analise, ou None.
# --------------------------------------------------------------------------
def rename(conn: sqlite3.Connection, name: str) -> None:
    if not name or not name.strip():
        raise ValueError("project name must not be empty")
    if identity(conn) is None:
        raise ValueError("this file is not a project (M03_Project is empty)")
    conn.execute("UPDATE M03_Project SET ProjectName = ?", (name.strip(),))


def summary(conn: sqlite3.Connection) -> dict | None:
    ident = identity(conn)
    if ident is None:
        return None
    row = conn.execute("SELECT Mode FROM D06_Analysis ORDER BY IDA DESC LIMIT 1").fetchone()
    return {**ident, "Mode": row[0] if row else None}
