"""Modelos de bateria e versoes de montagem do usuario (T46, B1).

Sem Streamlit. Copias editaveis dos registros da base: D15/D16 (bateria, prefixo UB-) e
D17/D18 (montagem, prefixo UA-). A base nunca muda. O calculo recebe as copias validas
no lugar dos registros da base (`merge_into_base`), pelo identificador.

Blocos:
    UA1  bateria
    UA2  montagem
    UA3  entregar ao calculo
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3

import pandas as pd

from .user_recipes import violations

BATTERY_PREFIX = "UB-"
ASSEMBLY_PREFIX = "UA-"


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _new_id(conn, ident, prefix, tabelas) -> str:
    ident = ident.strip()
    if not ident.startswith(prefix) or len(ident) <= len(prefix):
        raise ValueError(f"o identificador comeca por {prefix}")
    for tabela, coluna in tabelas:
        if conn.execute(f"SELECT 1 FROM {tabela} WHERE {coluna} = ?", (ident,)).fetchone():
            raise ValueError(f"ja existe um registro chamado {ident}")
    return ident


# --------------------------------------------------------------------------
# BLOCO UA1 -- bateria
#   I44: cada grupo fecha em 1 (1e-6) ou e todo zero; so material entra na soma.
# --------------------------------------------------------------------------
def copy_battery(conn: sqlite3.Connection, ident: str, base_id: str, name: str,
                 author: str = "") -> None:
    ident = _new_id(conn, ident, BATTERY_PREFIX,
                    [("P19_BatteryModel", "IDBMd"), ("D15_UserBatteryModel", "IDBMdU")])
    base = conn.execute("SELECT IDVPT, IDBTe, RefEnergy, RefPower, RefWeight FROM "
                        "P19_BatteryModel WHERE IDBMd = ?", (base_id,)).fetchone()
    if base is None:
        raise ValueError(f"o modelo de origem {base_id} nao existe na base")
    now = _now()
    conn.execute("INSERT INTO D15_UserBatteryModel (IDBMdU, DsBMdU, IDBMdBase, IDVPT, IDBTe, "
                 "RefEnergy, RefPower, RefWeight, Origin, Author, CreatedAt, UpdatedAt) "
                 "VALUES (?,?,?,?,?,?,?,?, 'Own', ?,?,?)",
                 (ident, name.strip() or ident, base_id, *base, author, now, now))
    conn.execute("INSERT INTO D16_UserBatteryShare (IDBMdU, IDGG, IDM, BMshareGG) "
                 "SELECT ?, IDGG, IDM, BMshareGG FROM P20_BatteryMaterialShare WHERE IDBMd = ?",
                 (ident, base_id))


def set_battery_share(conn: sqlite3.Connection, ident: str, idgg: str, idm: str,
                      value: float) -> None:
    if value < 0:
        raise ValueError("participacao de material nao e negativa")
    if conn.execute("SELECT 1 FROM D15_UserBatteryModel WHERE IDBMdU = ?",
                    (ident,)).fetchone() is None:
        raise ValueError(f"modelo {ident} nao existe")
    conn.execute("INSERT INTO D16_UserBatteryShare (IDBMdU, IDGG, IDM, BMshareGG) VALUES "
                 "(?,?,?,?) ON CONFLICT (IDBMdU, IDGG, IDM) DO UPDATE SET "
                 "BMshareGG = excluded.BMshareGG", (ident, idgg, idm, float(value)))
    conn.execute("UPDATE D15_UserBatteryModel SET UpdatedAt = ? WHERE IDBMdU = ?",
                 (_now(), ident))


def check_battery(conn: sqlite3.Connection, ident: str) -> list[str]:
    p09 = pd.read_sql_query("SELECT IDM, ShareRole FROM P09_Material", conn)
    sh = pd.read_sql_query("SELECT IDGG, IDM, BMshareGG AS MshareGG FROM D16_UserBatteryShare "
                           "WHERE IDBMdU = ?", conn, params=(ident,))
    return violations(sh, p09)


# --------------------------------------------------------------------------
# BLOCO UA2 -- montagem
# --------------------------------------------------------------------------
def copy_assembly(conn: sqlite3.Connection, ident: str, base_id: str, name: str,
                  author: str = "") -> None:
    ident = _new_id(conn, ident, ASSEMBLY_PREFIX,
                    [("P23_AssemblyParamVersion", "IDAPV"), ("D17_UserAssemblyVersion", "IDAPVU")])
    base = conn.execute("SELECT Method, FixedGHGPerVehicle FROM P23_AssemblyParamVersion "
                        "WHERE IDAPV = ?", (base_id,)).fetchone()
    if base is None:
        raise ValueError(f"a versao de origem {base_id} nao existe na base")
    now = _now()
    conn.execute("INSERT INTO D17_UserAssemblyVersion (IDAPVU, DsAPVU, Method, "
                 "FixedGHGPerVehicle, Origin, Author, CreatedAt, UpdatedAt) "
                 "VALUES (?,?,?,?, 'Own', ?,?,?)",
                 (ident, name.strip() or ident, *base, author, now, now))
    conn.execute("INSERT INTO D18_UserAssemblyEnergy (IDAPVU, IDAP, IDFuel, EnergyPerVehicle, "
                 "FuelShare) SELECT ?, IDAP, IDFuel, EnergyPerVehicle, FuelShare FROM "
                 "P22_AssemblyEnergy WHERE IDAPV = ?", (ident, base_id))


def set_assembly_energy(conn: sqlite3.Connection, ident: str, idap: int, idfuel: str,
                        energy: float, share: float) -> None:
    if energy < 0 or not 0 <= share <= 1:
        raise ValueError("energia nao e negativa e a participacao fica entre 0 e 1")
    conn.execute("INSERT INTO D18_UserAssemblyEnergy (IDAPVU, IDAP, IDFuel, EnergyPerVehicle, "
                 "FuelShare) VALUES (?,?,?,?,?) ON CONFLICT (IDAPVU, IDAP, IDFuel) DO UPDATE "
                 "SET EnergyPerVehicle = excluded.EnergyPerVehicle, "
                 "FuelShare = excluded.FuelShare", (ident, idap, idfuel, float(energy),
                                                    float(share)))
    conn.execute("UPDATE D17_UserAssemblyVersion SET UpdatedAt = ? WHERE IDAPVU = ?",
                 (_now(), ident))


# --------------------------------------------------------------------------
# BLOCO UA3 -- entregar ao calculo (em memoria)
# --------------------------------------------------------------------------
def merge_into_base(tables: dict[str, pd.DataFrame]) -> None:
    d15, d16 = tables.get("D15"), tables.get("D16")
    if d15 is not None and d16 is not None and not d15.empty:
        validos, linhas = [], []
        for _, m in d15.iterrows():
            sh = d16[d16["IDBMdU"] == m["IDBMdU"]].rename(columns={"BMshareGG": "MshareGG"})
            origem = tables["P19"][tables["P19"]["IDBMd"] == m["IDBMdBase"]]
            if violations(sh, tables["P09"]) or origem.empty:
                continue
            nova = origem.iloc[0].copy()
            nova["IDBMd"], nova["DsBMd"] = m["IDBMdU"], m["DsBMdU"]
            for col, dst in (("IDVPT", "IDVPT"), ("IDBTe", "IDBTe"), ("RefEnergy", "RefEnergy"),
                             ("RefPower", "RefPower"), ("RefWeight", "RefWeight")):
                if pd.notna(m[col]):
                    nova[dst] = m[col]
            validos.append(nova)
            linhas.append(d16[d16["IDBMdU"] == m["IDBMdU"]]
                          .rename(columns={"IDBMdU": "IDBMd"}))
        if validos:
            tables["P19"] = pd.concat([tables["P19"], pd.DataFrame(validos)], ignore_index=True)
            tables["P20"] = pd.concat([tables["P20"], *linhas], ignore_index=True)
    d17, d18 = tables.get("D17"), tables.get("D18")
    if d17 is not None and d18 is not None and not d17.empty:
        p23 = pd.DataFrame({"IDAPV": d17["IDAPVU"], "DsAPV": d17["DsAPVU"],
                            "DateIDAPV": d17["UpdatedAt"], "Method": d17["Method"],
                            "FixedGHGPerVehicle": d17["FixedGHGPerVehicle"],
                            "Status": "recommended", "IDEFVdefault": None,
                            "SourceAPV": "Versao do usuario (" + d17["Origin"] + ")"})
        p22 = d18.rename(columns={"IDAPVU": "IDAPV"})
        tables["P23"] = pd.concat([tables["P23"], p23], ignore_index=True)
        tables["P22"] = pd.concat([tables["P22"], p22], ignore_index=True)


def assembly_hash(conn: sqlite3.Connection, idapvu: str) -> str:
    """Impressao digital da energia de uma montagem do usuario (I53)."""
    rows = conn.execute("SELECT IDAP, IDFuel, EnergyPerVehicle, FuelShare FROM "
                        "D18_UserAssemblyEnergy WHERE IDAPVU = ? ORDER BY IDAP, IDFuel",
                        (idapvu,)).fetchall()
    return hashlib.sha256(repr(rows).encode("utf-8")).hexdigest()
