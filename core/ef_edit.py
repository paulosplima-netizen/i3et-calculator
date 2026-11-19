"""Edicao dos fatores de emissao no arquivo do projeto (T15, B1).

Sem Streamlit. A base de referencia nao muda. Decisao 11 (19/11/2026):

* lista `Typed` (digitada na base) e lista `Own` (do usuario) sao editaveis; a
  alteracao fica no arquivo do projeto, em D05, sobre o valor da base;
* lista `Published` (cita uma fonte) e bloqueada; para mudar um valor, copie-a
  antes para uma versao `Typed` (D04, com `BasedOnIDEFV`);
* toda alteracao vai para D19 com autor, data e motivo, e a lista passa a ser
  apresentada como "alterada" (`status`);
* `factors_hash` e a impressao digital dos fatores efetivos de uma lista (I53).

Blocos:
    EF1  versoes
    EF2  fatores (sobrepor, restaurar)
    EF3  comparar versoes
    EF4  estado, correcoes e impressao digital (I53)
"""

from __future__ import annotations

import datetime as dt
import hashlib
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
                   source: str, author: str = "", origin: str = "Own") -> None:
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
        "LicenseEFV, BasedOnIDEFV, Origin) VALUES (?,?,?,?,?,?,?,?)",
        (idefv, description.strip(), dt.date.today().isoformat(), row[0], source.strip(),
         "Definido pelo usuario deste projeto.", based_on, origin))


def copy_to_typed(conn: sqlite3.Connection, source_idefv: str, new_idefv: str, *,
                  reason: str, author: str = "") -> None:
    """Copia uma lista da base (em geral uma `Published`) para uma versao `Typed`.

    E o caminho para alterar valores de uma lista publicada: a copia herda todos os
    fatores, guarda a lista de origem em `BasedOnIDEFV` e a fonte cita essa origem,
    de modo que a citacao da fonte original nao passa a valer para os valores
    alterados. O motivo e obrigatorio.
    """
    if not reason.strip():
        raise ValueError("o motivo da copia e obrigatorio (I49)")
    create_version(conn, new_idefv, f"Copia digitada de {source_idefv}", source_idefv,
                   f"Copia de {source_idefv}: {reason.strip()}", author, origin="Typed")


def origin(conn: sqlite3.Connection, idefv: str) -> str | None:
    """`Typed`, `Published` ou `Own`; None se a versao nao existe."""
    for tabela in ("P10_EFVersion", "D04_UserEFVersion"):
        r = conn.execute(f"SELECT Origin FROM {tabela} WHERE IDEFV = ?", (idefv,)).fetchone()
        if r:
            return r[0]
    return None


def is_editable(conn: sqlite3.Connection, idefv: str) -> bool:
    """Listas `Typed` e `Own` recebem sobrescrita; as `Published` ficam como estao (I48)."""
    return origin(conn, idefv) in ("Typed", "Own")


# --------------------------------------------------------------------------
# BLOCO EF2 -- fatores
#   I48 a base e imutavel; I49 motivo obrigatorio; I50 zero so com `confirm_zero`;
#   restaurar volta ao valor herdado (ou a ausencia de dado) e registra `restore`.
# --------------------------------------------------------------------------
def inherited_value(conn: sqlite3.Connection, idefv: str, idm: str) -> float | None:
    """Valor sem a alteracao do usuario: o da base (P10) ou o da lista de origem (D04)."""
    r = conn.execute(
        "SELECT p.EF FROM D04_UserEFVersion d JOIN P11_EmissionFactor p "
        "ON p.IDEFV = d.BasedOnIDEFV WHERE d.IDEFV = ? AND p.IDM = ?", (idefv, idm)).fetchone()
    if r is None:
        r = conn.execute("SELECT EF FROM P11_EmissionFactor WHERE IDEFV = ? AND IDM = ?",
                         (idefv, idm)).fetchone()
    return None if r is None or r[0] is None else float(r[0])


def set_factor(conn: sqlite3.Connection, idefv: str, idm: str, ef: float, *, reason: str,
               author: str = "", confirm_zero: bool = False) -> None:
    kind = origin(conn, idefv)
    if kind is None:
        raise ValueError(f"a versao {idefv} nao existe (I59)")
    if kind == "Published":
        raise ValueError(f"{idefv} e uma lista publicada e nao pode ser editada (I48); "
                         "copie-a antes para uma versao digitada")
    if not reason.strip():
        raise ValueError("o motivo da alteracao e obrigatorio (I49)")
    if ef < 0:
        raise ValueError("o fator nao pode ser negativo")
    if ef == 0 and not confirm_zero:
        raise ValueError("zero explicito exige confirmacao e motivo documentado (I50)")
    old = conn.execute("SELECT EF FROM D05_UserEmissionFactor WHERE IDEFV = ? AND IDM = ?",
                       (idefv, idm)).fetchone()
    previous = float(old[0]) if old else inherited_value(conn, idefv, idm)
    conn.execute("INSERT INTO D05_UserEmissionFactor (IDM, IDEFV, EF, EFnotes, Author, "
                 "ChangedAt, Reason) VALUES (?,?,?,?,?,?,?) "
                 "ON CONFLICT (IDM, IDEFV) DO UPDATE SET EF = excluded.EF, "
                 "EFnotes = excluded.EFnotes, Author = excluded.Author, "
                 "ChangedAt = excluded.ChangedAt, Reason = excluded.Reason",
                 (idm, idefv, float(ef), reason.strip(), author, _now(), reason.strip()))
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


# --------------------------------------------------------------------------
# BLOCO EF4 -- estado, correcoes e impressao digital (I53)
#   status          : origem, se e editavel, quantos fatores mudaram, lista de origem e
#                     o rotulo que as telas e o relatorio mostram.
#   corrections     : cada fator alterado, com o valor da base e o novo, para levar a
#                     correcao de volta a planilha e a base.
#   factors_hash    : SHA-256 dos fatores efetivos da lista (IDM e valor, em ordem).
#                     A rodada congelada guarda o hash; se os fatores mudarem depois,
#                     o congelamento deixa de valer (I53).
# --------------------------------------------------------------------------
def n_changed(conn: sqlite3.Connection, idefv: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM D05_UserEmissionFactor WHERE IDEFV = ?",
                        (idefv,)).fetchone()[0]


def status(conn: sqlite3.Connection, idefv: str) -> dict:
    kind = origin(conn, idefv)
    row = conn.execute("SELECT BasedOnIDEFV FROM D04_UserEFVersion WHERE IDEFV = ?",
                       (idefv,)).fetchone()
    derived = row[0] if row else None
    changed = n_changed(conn, idefv)
    label = {"Typed": "Typed", "Published": "Published", "Own": "Own", None: ""}[kind]
    if derived and kind in ("Typed", "Own"):
        label += f", derived from {derived}"
    if changed and kind != "Published":
        label += ", altered"
    return {"origin": kind, "editable": is_editable(conn, idefv), "changed": changed,
            "derived_from": derived, "label": label}


def corrections(conn: sqlite3.Connection, idefv: str | None = None) -> pd.DataFrame:
    """Fatores alterados pelo usuario, com o valor original da base."""
    sql = ("SELECT d.IDEFV, d.IDM, m.DsM, d.EF AS NewEF, d.Author, d.ChangedAt, d.Reason "
           "FROM D05_UserEmissionFactor d LEFT JOIN P09_Material m ON m.IDM = d.IDM")
    args: tuple = ()
    if idefv is not None:
        sql += " WHERE d.IDEFV = ?"
        args = (idefv,)
    out = pd.read_sql_query(sql + " ORDER BY d.IDEFV, d.IDM", conn, params=args)
    out["OriginalEF"] = [inherited_value(conn, a, b) for a, b in zip(out["IDEFV"], out["IDM"])]
    return out[["IDEFV", "IDM", "DsM", "OriginalEF", "NewEF", "Author", "ChangedAt", "Reason"]]


def effective_pairs(conn: sqlite3.Connection, idefv: str) -> list[tuple[str, float | None]]:
    rows = conn.execute("SELECT IDM, EF FROM EF_Effective WHERE IDEFV = ? ORDER BY IDM",
                        (idefv,)).fetchall()
    return [(str(a), None if b is None else float(b)) for a, b in rows]


def factors_hash(conn: sqlite3.Connection, idefv: str) -> str:
    h = hashlib.sha256()
    for idm, ef in effective_pairs(conn, idefv):
        h.update(f"{idm}={ef!r};".encode("utf-8"))
    return h.hexdigest()


def needs_hash(conn: sqlite3.Connection, idefv: str) -> bool:
    """So listas do usuario ou alteradas guardam o hash; as da base ja estao em ParamBaseHash."""
    return status(conn, idefv)["changed"] > 0 or origin(conn, idefv) in ("Own",) or bool(
        conn.execute("SELECT 1 FROM D04_UserEFVersion WHERE IDEFV = ?", (idefv,)).fetchone())


def orphans(conn: sqlite3.Connection) -> list[str]:
    """Linhas de D05 cuja lista nao existe nem em P10 nem em D04 (I59)."""
    rows = conn.execute(
        "SELECT DISTINCT IDEFV FROM D05_UserEmissionFactor WHERE IDEFV NOT IN "
        "(SELECT IDEFV FROM P10_EFVersion UNION SELECT IDEFV FROM D04_UserEFVersion)").fetchall()
    return [r[0] for r in rows]
