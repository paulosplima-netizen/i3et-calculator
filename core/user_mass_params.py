"""Copia editavel dos parametros de estimativa de massa (T13, B1): D20 e D21.

Sem Streamlit. Prefixo UM-. A base (P05, P06) nao muda. Regra I58: MR >= 0, GCR > 0,
fLM >= 0 (ver docs/09). `merge_into_base` entrega as copias ao calculo no lugar da
versao da base, em memoria, pelo identificador.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3

import pandas as pd

PREFIX = "UM-"


def preview(mr: float, gc: float, gcr: float, beta: float, flm: float = 1.0) -> float:
    """ME = MR x (GC / GCR)^beta x fLM; indeterminado vale 0, como o IFERROR da planilha."""
    try:
        return float(mr) * (float(gc) / float(gcr)) ** float(beta) * float(flm)
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0.0


def copy_version(conn: sqlite3.Connection, ident: str, base_id: int, name: str,
                 author: str = "", notes: str = "") -> None:
    ident = ident.strip()
    if not ident.startswith(PREFIX) or len(ident) <= len(PREFIX):
        raise ValueError(f"o identificador comeca por {PREFIX}")
    if conn.execute("SELECT 1 FROM D20_UserMassParamVersion WHERE IDMPVU = ?",
                    (ident,)).fetchone():
        raise ValueError(f"ja existe uma versao chamada {ident}")
    if conn.execute("SELECT 1 FROM P05_MassParamVersion WHERE IDMPV = ?",
                    (base_id,)).fetchone() is None:
        raise ValueError(f"a versao de origem {base_id} nao existe na base")
    now = dt.datetime.now().isoformat(timespec="seconds")
    conn.execute("INSERT INTO D20_UserMassParamVersion (IDMPVU, DsMPVU, IDMPVBase, Origin, "
                 "Author, CreatedAt, NotesMPV) VALUES (?,?,?, 'Own', ?,?,?)",
                 (ident, name.strip() or ident, base_id, author, now, notes))
    conn.execute("INSERT INTO D21_UserMassParam (IDMPVU, IDSG, Beta, GCR, utGCR, MR, fLM, "
                 "Reference, ChangedBy, ChangedAt) SELECT ?, IDSG, Beta, GCR, utGCR, MR, fLM, "
                 "Reference, ?, ? FROM P06_MassEstimationParam WHERE IDMPV = ?",
                 (ident, author, now, base_id))


def set_param(conn: sqlite3.Connection, ident: str, idsg: int, *, beta: float, gcr: float,
              mr: float, flm: float, reference: str = "", author: str = "") -> None:
    if mr < 0 or gcr <= 0 or flm < 0 or beta < 0:
        raise ValueError("MR, beta e fLM nao sao negativos e GCR e maior que zero (I58)")
    if conn.execute("SELECT 1 FROM D21_UserMassParam WHERE IDMPVU = ? AND IDSG = ?",
                    (ident, idsg)).fetchone() is None:
        raise ValueError(f"o subgrupo {idsg} nao existe na versao {ident}")
    now = dt.datetime.now().isoformat(timespec="seconds")
    conn.execute("UPDATE D21_UserMassParam SET Beta = ?, GCR = ?, MR = ?, fLM = ?, "
                 "Reference = ?, ChangedBy = ?, ChangedAt = ? WHERE IDMPVU = ? AND IDSG = ?",
                 (beta, gcr, mr, flm, reference, author, now, ident, idsg))


def merge_into_base(tables: dict[str, pd.DataFrame]) -> None:
    d20, d21 = tables.get("D20"), tables.get("D21")
    if d20 is None or d21 is None or d20.empty:
        return
    novos = []
    for _, v in d20.iterrows():
        sub = d21[d21["IDMPVU"] == v["IDMPVU"]].rename(columns={"IDMPVU": "IDMPV"})
        novos.append(sub[["IDMPV", "IDSG", "Beta", "GCR", "utGCR", "MR", "fLM", "Reference"]])
    p05 = pd.DataFrame({"IDMPV": d20["IDMPVU"], "DsMPV": d20["DsMPVU"],
                        "DateIDMPV": d20["CreatedAt"], "SourceMPV": "Versao do usuario"})
    tables["P05"] = pd.concat([tables["P05"], p05], ignore_index=True)
    tables["P06"] = pd.concat([tables["P06"], *novos], ignore_index=True)


def params_hash(conn: sqlite3.Connection, idmpvu: str) -> str:
    """Impressao digital dos parametros de massa de uma copia do usuario (I53)."""
    rows = conn.execute("SELECT IDSG, Beta, GCR, utGCR, MR, fLM FROM D21_UserMassParam "
                        "WHERE IDMPVU = ? ORDER BY IDSG", (idmpvu,)).fetchall()
    return hashlib.sha256(repr(rows).encode("utf-8")).hexdigest()
