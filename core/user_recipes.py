"""Receitas de materiais do usuario (T14, B1): D13 (cabecalho) e D14 (participacoes).

Sem Streamlit. A receita do usuario nasce como copia de uma da base (P15 e P16), que
nunca e alterada. Rascunho com violacao (I29) pode ser salvo, mas nao pode ser
escolhido numa analise: `merge_into_base` so entrega a quem calcula as receitas validas.

Blocos:
    UR1  verificar (I29)
    UR2  copiar e editar
    UR3  entregar ao calculo
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3

import pandas as pd

TOL = 1e-6
PREFIX = "U-"


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# BLOCO UR1 -- verificar
#   I29: cada grupo nao vazio fecha em 1 (tolerancia 1e-6) ou e todo zero; so
#   participacao de material entra na soma (processo e detalhamento, nao).
# --------------------------------------------------------------------------
def violations(shares: pd.DataFrame, p09: pd.DataFrame) -> list[str]:
    material = set(p09.loc[p09["ShareRole"] == "material", "IDM"].astype(str))
    s = shares[shares["IDM"].astype(str).isin(material)]
    out = []
    for grupo, soma in s.groupby("IDGG")["MshareGG"].sum().items():
        if abs(soma) > TOL and abs(soma - 1.0) > TOL:
            out.append(f"grupo {grupo}: soma das participacoes = {soma:.6f} (deve ser 1 ou 0)")
    return out


def _shares(conn, idvmru) -> pd.DataFrame:
    return pd.read_sql_query("SELECT IDGG, IDM, MshareGG FROM D14_UserMaterialShare "
                             "WHERE IDVMRU = ?", conn, params=(idvmru,))


def check(conn: sqlite3.Connection, idvmru: str) -> list[str]:
    p09 = pd.read_sql_query("SELECT IDM, ShareRole FROM P09_Material", conn)
    return violations(_shares(conn, idvmru), p09)


def valid_ids(conn: sqlite3.Connection) -> list[str]:
    ids = [r[0] for r in conn.execute("SELECT IDVMRU FROM D13_UserRecipe ORDER BY IDVMRU")]
    return [i for i in ids if not check(conn, i)]


def shares_hash(conn: sqlite3.Connection, idvmru: str) -> str:
    rows = conn.execute("SELECT IDGG, IDM, MshareGG FROM D14_UserMaterialShare WHERE IDVMRU = ? "
                        "ORDER BY IDGG, IDM", (idvmru,)).fetchall()
    return hashlib.sha256(repr(rows).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# BLOCO UR2 -- copiar e editar
# --------------------------------------------------------------------------
def copy_recipe(conn: sqlite3.Connection, idvmru: str, base_id: str, name: str,
                author: str = "", notes: str = "") -> None:
    idvmru = idvmru.strip()
    if not idvmru.startswith(PREFIX) or len(idvmru) <= len(PREFIX):
        raise ValueError(f"o identificador da receita do usuario comeca por {PREFIX}")
    if conn.execute("SELECT 1 FROM P15_VehicleMaterialRecipe WHERE IDVMR = ? UNION "
                    "SELECT 1 FROM D13_UserRecipe WHERE IDVMRU = ?",
                    (idvmru, idvmru)).fetchone():
        raise ValueError(f"ja existe uma receita chamada {idvmru}")
    base = conn.execute("SELECT IDVPT, COALESCE(IDVDT, ''), COALESCE(IDVS, '') "
                        "FROM P15_VehicleMaterialRecipe WHERE IDVMR = ?", (base_id,)).fetchone()
    if base is None:
        raise ValueError(f"a receita de origem {base_id} nao existe na base")
    now = _now()
    conn.execute("INSERT INTO D13_UserRecipe (IDVMRU, DsVMRU, IDVMRBase, IDVPT, IDVDT, IDVS, "
                 "Author, CreatedAt, UpdatedAt, NotesU) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (idvmru, name.strip() or idvmru, base_id, *base, author, now, now, notes))
    conn.execute("INSERT INTO D14_UserMaterialShare (IDVMRU, IDGG, IDM, MshareGG, ChangedBy, "
                 "ChangedAt) SELECT ?, IDGG, IDM, MshareGG, ?, ? FROM P16_MaterialShare "
                 "WHERE IDVMR = ?", (idvmru, author, now, base_id))


def set_share(conn: sqlite3.Connection, idvmru: str, idgg: str, idm: str, value: float, *,
              source: str = "", author: str = "") -> None:
    if value < 0:
        raise ValueError("participacao de material nao e negativa (I29)")
    head = conn.execute("SELECT IDVMRBase FROM D13_UserRecipe WHERE IDVMRU = ?",
                        (idvmru,)).fetchone()
    if head is None:
        raise ValueError(f"receita {idvmru} nao existe")
    orig = conn.execute("SELECT MshareGG FROM P16_MaterialShare WHERE IDVMR = ? AND IDGG = ? "
                        "AND IDM = ?", (head[0], idgg, idm)).fetchone()
    if abs(value - (orig[0] if orig else 0.0)) > 1e-12 and not source.strip():
        raise ValueError("a fonte e obrigatoria quando o valor difere da receita de origem")
    now = _now()
    conn.execute("INSERT INTO D14_UserMaterialShare (IDVMRU, IDGG, IDM, MshareGG, SourceU, "
                 "ChangedBy, ChangedAt) VALUES (?,?,?,?,?,?,?) ON CONFLICT (IDVMRU, IDGG, IDM) "
                 "DO UPDATE SET MshareGG = excluded.MshareGG, SourceU = excluded.SourceU, "
                 "ChangedBy = excluded.ChangedBy, ChangedAt = excluded.ChangedAt",
                 (idvmru, idgg, idm, float(value), source.strip(), author, now))
    conn.execute("UPDATE D13_UserRecipe SET UpdatedAt = ? WHERE IDVMRU = ?", (now, idvmru))


def normalize_group(conn: sqlite3.Connection, idvmru: str, idgg: str, *,
                    author: str = "") -> bool:
    """Divide as participacoes de material do grupo pela soma; processo fica como esta."""
    rows = conn.execute(
        "SELECT d.IDM, d.MshareGG FROM D14_UserMaterialShare d JOIN P09_Material p "
        "ON p.IDM = d.IDM WHERE d.IDVMRU = ? AND d.IDGG = ? AND p.ShareRole = 'material'",
        (idvmru, idgg)).fetchall()
    total = sum(v for _, v in rows)
    if total <= 0:
        return False
    now = _now()
    for idm, v in rows:
        conn.execute("UPDATE D14_UserMaterialShare SET MshareGG = ?, ChangedBy = ?, "
                     "ChangedAt = ? WHERE IDVMRU = ? AND IDGG = ? AND IDM = ?",
                     (v / total, author, now, idvmru, idgg, idm))
    conn.execute("UPDATE D13_UserRecipe SET UpdatedAt = ? WHERE IDVMRU = ?", (now, idvmru))
    return True


# --------------------------------------------------------------------------
# BLOCO UR3 -- entregar ao calculo
#   As receitas validas entram em P15 e P16 (so em memoria); o calculo as le como as da base.
# --------------------------------------------------------------------------
def merge_into_base(tables: dict[str, pd.DataFrame]) -> None:
    d13, d14 = tables.get("D13"), tables.get("D14")
    if d13 is None or d14 is None or d13.empty:
        return
    validos = []
    for idvmru, grupo in d14.groupby("IDVMRU"):
        if not violations(grupo, tables["P09"]):
            validos.append(idvmru)
    cab = d13[d13["IDVMRU"].isin(validos)]
    if cab.empty:
        return
    novo15 = pd.DataFrame({"IDVMR": cab["IDVMRU"], "IDVPT": cab["IDVPT"],
                           "IDVDT": cab["IDVDT"], "IDVS": cab["IDVS"], "DsVMR": cab["DsVMRU"]})
    linhas = d14[d14["IDVMRU"].isin(validos)]
    novo16 = linhas.rename(columns={"IDVMRU": "IDVMR"})[["IDVMR", "IDGG", "IDM", "MshareGG"]]
    tables["P15"] = pd.concat([tables["P15"], novo15], ignore_index=True)
    tables["P16"] = pd.concat([tables["P16"], novo16], ignore_index=True)
