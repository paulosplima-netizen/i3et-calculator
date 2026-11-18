"""Edicao dos fatores de emissao no arquivo do projeto (T15, B1).

Sem Streamlit. A base de referencia nao muda: o usuario cria uma versao propria
(D04), herdada de uma versao da base, e sobrepoe fatores em D05. Toda alteracao
vai para D19 com autor, data e motivo.

Blocos:
    EF1  versoes
    EF2  fatores (sobrepor, restaurar)
    EF3  comparar versoes
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import pandas as pd


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# BLOCO EF1 -- versoes
#   I51: ID unico (nao pode existir em P10 nem em D04), fonte obrigatoria e
#   versao de origem existente em P10. A copia herda GWP e nao herda a licenca.
# --------------------------------------------------------------------------
def create_version(conn: sqlite3.Connection, idefv: str, description: str, based_on: str,
                   source: str, author: str = "") -> None:
    idefv = idefv.strip()
    if not idefv:
        raise ValueError("o identificador da versao e obrigatorio")
    if not source.strip():
        raise ValueError("a fonte dos valores e obrigatoria (I51)")
    if conn.execute("SELECT 1 FROM P10_EFVersion WHERE IDEFV = ? UNION "
                    "SELECT 1 FROM D04_UserEFVersion WHERE IDEFV = ?",
                    (idefv, idefv)).fetchone():
        raise ValueError(f"ja existe uma versao chamada {idefv} (I51)")
    row = conn.execute("SELECT GWPSet FROM P10_EFVersion WHERE IDEFV = ?",
                       (based_on,)).fetchone()
    if row is None:
        raise ValueError(f"a versao de origem {based_on} nao existe (I51)")
    conn.execute(
        "INSERT INTO D04_UserEFVersion (IDEFV, DsEFV, DateIDEFV, GWPSet, SourceEFV, "
        "LicenseEFV, BasedOnIDEFV, Origin) VALUES (?,?,?,?,?,?,?, 'Own')",
        (idefv, description.strip(), dt.date.today().isoformat(), row[0], source.strip(),
         "Definido pelo usuario deste projeto.", based_on))


def origin(conn: sqlite3.Connection, idefv: str) -> str | None:
    """`Typed`, `Published` ou `Own`; None se a versao nao existe."""
    for tabela in ("P10_EFVersion", "D04_UserEFVersion"):
        r = conn.execute(f"SELECT Origin FROM {tabela} WHERE IDEFV = ?", (idefv,)).fetchone()
        if r:
            return r[0]
    return None


def is_editable(conn: sqlite3.Connection, idefv: str) -> bool:
    """So versoes proprias (D04) recebem sobrescrita; as da base ficam como estao (I48)."""
    return conn.execute("SELECT 1 FROM D04_UserEFVersion WHERE IDEFV = ?",
                        (idefv,)).fetchone() is not None


# --------------------------------------------------------------------------
# BLOCO EF2 -- fatores
#   I48 a base e imutavel; I49 motivo obrigatorio; I50 zero so com `confirm_zero`;
#   restaurar volta ao valor herdado (ou a ausencia de dado) e registra `restore`.
# --------------------------------------------------------------------------
def inherited_value(conn: sqlite3.Connection, idefv: str, idm: str) -> float | None:
    r = conn.execute(
        "SELECT p.EF FROM D04_UserEFVersion d JOIN P11_EmissionFactor p "
        "ON p.IDEFV = d.BasedOnIDEFV WHERE d.IDEFV = ? AND p.IDM = ?", (idefv, idm)).fetchone()
    return None if r is None or r[0] is None else float(r[0])


def set_factor(conn: sqlite3.Connection, idefv: str, idm: str, ef: float, *, reason: str,
               author: str = "", confirm_zero: bool = False) -> None:
    if not is_editable(conn, idefv):
        raise ValueError(f"{idefv} e da base de referencia e nao pode ser editada (I48); "
                         "crie uma versao propria")
    if not reason.strip():
        raise ValueError("o motivo da alteracao e obrigatorio (I49)")
    if ef < 0:
        raise ValueError("o fator nao pode ser negativo")
    if ef == 0 and not confirm_zero:
        raise ValueError("zero explicito exige confirmacao e motivo documentado (I50)")
    old = conn.execute("SELECT EF FROM D05_UserEmissionFactor WHERE IDEFV = ? AND IDM = ?",
                       (idefv, idm)).fetchone()
    previous = float(old[0]) if old else inherited_value(conn, idefv, idm)
    conn.execute("INSERT INTO D05_UserEmissionFactor (IDM, IDEFV, EF, EFnotes) VALUES (?,?,?,?) "
                 "ON CONFLICT (IDM, IDEFV) DO UPDATE SET EF = excluded.EF, "
                 "EFnotes = excluded.EFnotes", (idm, idefv, float(ef), reason.strip()))
    _log(conn, idefv, idm, "override" if old is None else "edit", previous, float(ef),
         author, reason)


def restore_factor(conn: sqlite3.Connection, idefv: str, idm: str, *, reason: str,
                   author: str = "") -> bool:
    if not reason.strip():
        raise ValueError("o motivo da alteracao e obrigatorio (I49)")
    old = conn.execute("SELECT EF FROM D05_UserEmissionFactor WHERE IDEFV = ? AND IDM = ?",
                       (idefv, idm)).fetchone()
    if old is None:
        return False
    conn.execute("DELETE FROM D05_UserEmissionFactor WHERE IDEFV = ? AND IDM = ?", (idefv, idm))
    _log(conn, idefv, idm, "restore", float(old[0]), inherited_value(conn, idefv, idm),
         author, reason)
    return True


def _log(conn, idefv, idm, action, old, new, author, reason) -> None:
    conn.execute("INSERT INTO D19_EFChangeLog (IDEFV, IDM, Action, OldEF, NewEF, Author, "
                 "ChangedAt, Reason) VALUES (?,?,?,?,?,?,?,?)",
                 (idefv, idm, action, old, new, author, _now(), reason.strip()))


# --------------------------------------------------------------------------
# BLOCO EF3 -- comparar
#   Devolve : DataFrame IDM, DsM, EF_a, EF_b, Diff, DiffPct, e o aviso de GWP (I52).
# --------------------------------------------------------------------------
def compare(effective: pd.DataFrame, materials: pd.DataFrame, a: str, b: str,
            gwp: dict[str, str]) -> tuple[pd.DataFrame, str | None]:
    ea = effective[effective["IDEFV"] == a].set_index("IDM")["EF"]
    eb = effective[effective["IDEFV"] == b].set_index("IDM")["EF"]
    out = pd.DataFrame({"EF_a": ea, "EF_b": eb}).reset_index().rename(columns={"index": "IDM"})
    out = out.merge(materials[["IDM", "DsM", "EFBasis"]], on="IDM", how="left")
    out["Diff"] = out["EF_b"] - out["EF_a"]
    out["DiffPct"] = 100 * out["Diff"] / out["EF_a"].where(out["EF_a"] != 0)
    aviso = None
    if gwp.get(a) != gwp.get(b):
        aviso = (f"As versoes usam conjuntos de GWP diferentes ({gwp.get(a)} e "
                 f"{gwp.get(b)}); a comparacao exige verificacao metodologica (I52).")
    return out, aviso
