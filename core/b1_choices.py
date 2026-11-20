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


# --------------------------------------------------------------------------
# BLOCO CH4 -- parcela da diferenca de massa para a carroceria (s)
#   Decisao de 19/11/2026: o padrao e a participacao da carroceria nas massas
#   estimadas do proprio veiculo (s = A_est / (A_est + B_est)), calculada em
#   core/calc.py; so o valor informado pelo usuario a substitui. A proporcao
#   carroceria/chassi do GREET (P63) nao entra no calculo: serve de diagnostico
#   da calibracao dos betas e das massas de referencia (T38).
# --------------------------------------------------------------------------
SHARE_DEVIATION_WARN = 0.05      # |s estimado - s do GREET| a partir do qual a T38 avisa


# --------------------------------------------------------------------------
# BLOCO CH5 -- massa declarada efetiva e calibracao automatica (decisao de 20/11/2026)
#   O parametro 25 do veiculo e a massa conhecida quando e informado (veiculo de mercado); em
#   veiculo teorico (potencia e bateria variadas) ele e calculado e nao ha massa conhecida:
#   nao ha rateio, e a massa estimada e o resultado.
#   Precedencia da massa declarada: a digitada na T38 (D07.DeclaredMassKg), depois o parametro
#   25 informado. A calibracao e automatica para SizingOrigin = Manufacturer (padrao); nos
#   demais casos (inclusive ExcelReference, para manter a paridade) so com MassCalibrationMode
#   = 'ON'; 'OFF' desliga. Um ajuste manual (MassAdjustmentKg != 0) prevalece sobre o automatico.
# --------------------------------------------------------------------------
BASIS_TYPED = "DECLARED_TYPED"
BASIS_MARKET = "DECLARED_MARKET"
BASIS_ITERATIVE = "ESTIMATED_ITERATIVE"
BASIS_ESTIMATED = "ESTIMATED"
SOURCE_PARAM25 = "Parameter 25 (market vehicle)"
IDVP_MASS = 25


def param25_known(params: list[dict] | None) -> float | None:
    """Massa do parametro 25 quando e informada (nao calculada) e positiva; senao None."""
    for p in params or []:
        if int(p["IDVP"]) == IDVP_MASS:
            if not p.get("IsCalculated") and float(p.get("GC") or 0.0) > 0:
                return float(p["GC"])
            return None
    return None


def mass_basis(case: dict, params: list[dict] | None) -> dict:
    """{'declared_kg', 'source', 'basis', 'auto', 'default_auto'} do caso (D07 + parametros)."""
    typed = case.get("DeclaredMassKg")
    known = param25_known(params)
    if typed:
        declared, source, basis = float(typed), case.get("DeclaredSource") or "", BASIS_TYPED
    elif known is not None and (case.get("SizingOrigin") == "Manufacturer"
                                or case.get("MassCalibrationMode") == "ON"):
        declared, source, basis = known, SOURCE_PARAM25, BASIS_MARKET
    else:
        declared, source = None, ""
        basis = BASIS_ESTIMATED if known is not None else BASIS_ITERATIVE
    default_auto = declared is not None and case.get("SizingOrigin") == "Manufacturer"
    mode = case.get("MassCalibrationMode")
    auto = declared is not None and (mode == "ON" or (mode != "OFF" and default_auto))
    return {"declared_kg": declared, "source": source, "basis": basis, "auto": auto,
            "default_auto": default_auto}


def body_share(user_value: float | None) -> float | None:
    """s do usuario, ou None (o calculo usa a proporcao das massas estimadas)."""
    return None if user_value is None else float(user_value)


def reference_body_share(base, idvmr: str) -> float | None:
    """s = A/(A+B) do GREET para a receita (P63), so como referencia; None se nao ha."""
    p63 = base.get("P63")
    if p63 is None or not len(p63):
        return None
    hit = p63.loc[p63["IDVMR"] == idvmr, "BodyShareOfMassAdj"]
    return float(hit.iloc[0]) if len(hit) else None


def share_deviation(estimated: float | None, reference: float | None) -> float | None:
    """s estimado - s do GREET (pontos de participacao); None se falta um dos dois."""
    if estimated is None or reference is None:
        return None
    return float(estimated) - float(reference)
