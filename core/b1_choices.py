"""Escolhas do usuario do B1 por analise: manutencao (D10, D10_Item) e fim de vida (D06).

Sem Streamlit. As telas T16 e T17 leem e gravam aqui; run._snapshot congela o
que `load` devolve; b1_results usa `options`.

Blocos:
    CH1  ler
    CH2  gravar
    CH3  converter em Options
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from . import endoflife, maintenance
from .b1_results import Options

DEFAULT_EOL = "GLIDER_BATTERY"


# --------------------------------------------------------------------------
# BLOCO CH1 -- ler
#   Devolve : None se a analise nao tem escolha nenhuma (valem os padroes);
#             senao {"MaintenanceMode", "Scenario", "VehicleLifeKm", "EoLMethod",
#             "items": [{"IDMI", "IntervalKm", "Active"}]}.
# --------------------------------------------------------------------------
def load(conn: sqlite3.Connection, ida: int) -> dict | None:
    eol = conn.execute("SELECT EoLMethod FROM D06_Analysis WHERE IDA = ?", (ida,)).fetchone()
    eol = eol[0] if eol else DEFAULT_EOL
    row = conn.execute("SELECT IDMS, MaintenanceMode, Scenario, VehicleLifeKm "
                       "FROM D10_MaintenanceScenario WHERE IDA = ?", (ida,)).fetchone()
    if row is None and eol == DEFAULT_EOL:
        return None
    out = {"MaintenanceMode": "Sim", "Scenario": "REFERENCE", "VehicleLifeKm": None,
           "EoLMethod": eol, "items": []}
    if row is not None:
        out.update(MaintenanceMode=row[1], Scenario=row[2], VehicleLifeKm=row[3])
        out["items"] = [{"IDMI": i, "IntervalKm": k, "Active": bool(a)} for i, k, a in
                        conn.execute("SELECT IDMI, IntervalKm, Active FROM D10_Item "
                                     "WHERE IDMS = ? ORDER BY IDMI", (row[0],))]
    return out


# --------------------------------------------------------------------------
# BLOCO CH2 -- gravar
#   Regras: I32 modo valido; I33 intervalo > 0; vida > 0; metodo de fim de vida valido.
# --------------------------------------------------------------------------
def save_maintenance(conn: sqlite3.Connection, ida: int, *, mode: str, scenario: str,
                     vehicle_life_km: float | None, items: list[dict],
                     author: str = "") -> None:
    if mode not in maintenance.MODES:
        raise ValueError(f"modo de manutencao invalido: {mode!r}")
    if scenario not in ("REFERENCE", "USER"):
        raise ValueError(f"cenario invalido: {scenario!r}")
    if vehicle_life_km is not None and vehicle_life_km <= 0:
        raise ValueError("a vida do veiculo deve ser maior que zero")
    for it in items:
        if it.get("IntervalKm") is not None and it["IntervalKm"] <= 0:
            raise ValueError(f"intervalo do item {it['IDMI']} deve ser maior que zero (I33)")
    now = dt.datetime.now().isoformat(timespec="seconds")
    row = conn.execute("SELECT IDMS FROM D10_MaintenanceScenario WHERE IDA = ?",
                       (ida,)).fetchone()
    if row is None:
        idms = conn.execute(
            "INSERT INTO D10_MaintenanceScenario (IDA, MaintenanceMode, Scenario, "
            "VehicleLifeKm, Author, ChangedAt) VALUES (?,?,?,?,?,?)",
            (ida, mode, scenario, vehicle_life_km, author, now)).lastrowid
    else:
        idms = row[0]
        conn.execute("UPDATE D10_MaintenanceScenario SET MaintenanceMode = ?, Scenario = ?, "
                     "VehicleLifeKm = ?, Author = ?, ChangedAt = ? WHERE IDMS = ?",
                     (mode, scenario, vehicle_life_km, author, now, idms))
    conn.execute("DELETE FROM D10_Item WHERE IDMS = ?", (idms,))
    for it in items:
        conn.execute("INSERT INTO D10_Item (IDMS, IDMI, IntervalKm, Active) VALUES (?,?,?,?)",
                     (idms, it["IDMI"], it.get("IntervalKm"), 1 if it.get("Active", True) else 0))


def save_eol(conn: sqlite3.Connection, ida: int, method: str) -> None:
    if method not in endoflife.METHODS:
        raise ValueError(f"metodo de fim de vida invalido: {method!r}")
    conn.execute("UPDATE D06_Analysis SET EoLMethod = ? WHERE IDA = ?", (method, ida))


# --------------------------------------------------------------------------
# BLOCO CH3 -- converter
#   Intervalos e ativacao do usuario so valem com Scenario USER.
# --------------------------------------------------------------------------
def options(choices: dict | None, cp_values: dict[str, float]) -> Options:
    from .b1_results import options_from_control_params
    opt = options_from_control_params(cp_values)
    if not choices:
        return opt
    opt.maintenance_mode = choices["MaintenanceMode"]
    opt.eol_method = choices["EoLMethod"]
    if choices.get("VehicleLifeKm"):
        opt.life_km = float(choices["VehicleLifeKm"])
    if choices["Scenario"] == "USER":
        opt.intervals = {i["IDMI"]: i["IntervalKm"] for i in choices["items"]
                         if i["IntervalKm"] is not None}
        opt.active = {i["IDMI"]: i["Active"] for i in choices["items"]}
    return opt
