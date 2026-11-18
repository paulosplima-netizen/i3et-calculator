"""Saidas do bloco B1: C15, C16, C34 e C35 por veiculo e cenario.

Sem Streamlit. Junta os modulos do B1 (maintenance, endoflife, mass_calibration,
life_stages) ao resultado de calc.calculate_vehicle, e grava as linhas no banco.
Sem escolhas do usuario (D10, D06), valem os padroes: manutencao "Sim", vida do
painel (X74 x 1000 km), fim de vida Glider + bateria com X76 e X77.

Blocos:
    B1R1  escolhas (Options)
    B1R2  calculo de um veiculo
    B1R3  gravacao em C15, C16, C34 e C35
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import endoflife, life_stages, maintenance, mass_calibration

FLUIDS = ("77", "78", "79", "80", "81", "82", "83")
IDVP_ENERGY_BATTERY = 5


# --------------------------------------------------------------------------
# BLOCO B1R1 -- escolhas
# --------------------------------------------------------------------------
@dataclass
class Options:
    maintenance_mode: str = "Sim"
    life_km: float = 200000.0
    eol_method: str = "GLIDER_BATTERY"
    factor_glider: float = 0.2
    factor_battery: float = 20.0
    declared_mass_kg: float | None = None
    declared_source: str = ""
    intervals: dict | None = None          # {IDMI: km} do cenario do usuario
    active: dict | None = None             # {IDMI: bool}


def options_from_control_params(cp: dict[str, float], **extra) -> Options:
    """Padroes do painel: X74 (vida, 10^3 km), X76 e X77 (fim de vida)."""
    return Options(life_km=float(cp.get("X74", 200.0)) * 1000.0,
                   factor_glider=float(cp.get("X76", 0.2)),
                   factor_battery=float(cp.get("X77", 20.0)), **extra)


# --------------------------------------------------------------------------
# BLOCO B1R2 -- calculo
#   Le      : resultado de calc.calculate_vehicle, a base (P31, P31b), os FE da
#             lista do cenario {IDM: EF} e as escolhas.
#   Devolve : {"C15", "C16", "C34", "C35": DataFrames; "warnings": [str]}
# --------------------------------------------------------------------------
def _items(base, intervals: dict | None) -> list[dict]:
    itens = base["P31"].to_dict("records")
    for it in itens:
        it["IntervalKm"] = None if pd.isna(it["IntervalKm"]) else float(it["IntervalKm"])
        if intervals and it["IDMI"] in intervals:
            it["IntervalKm"] = intervals[it["IDMI"]]
    return itens


def ef_for(ef_table: pd.DataFrame, idefv: str) -> dict[str, float]:
    """Fatores da lista do cenario como {IDM: EF}; sem fator publicado vira None."""
    sub = ef_table[ef_table["IDEFV"] == idefv]
    return {str(r.IDM): (None if pd.isna(r.EF) else float(r.EF)) for r in sub.itertuples()}


def compute(res: dict, base, ef: dict[str, float], options: Options,
            boundary: str = "MAT_ASM") -> dict:
    avisos: list[str] = []
    itens = _items(base, options.intervals)
    partes: dict[str, dict[str, float]] = {}
    for r in base["P31b"].itertuples():
        partes.setdefault(r.IDMI, {})[str(r.IDM)] = float(r.Share)

    c03, c02, c10 = res["C03"], res["C02"], res["C10"]
    fluidos = c03[(c03["IDGG"] == "K") & (c03["IDM"].astype(str).isin(FLUIDS))]
    massa_fluido = {str(r.IDM): float(r.MassIDMpGG) for r in fluidos.itertuples()}

    usados = {str(i["IDM"]) for i in itens if i["ItemKind"] == "FLUID" and i["IDM"]}
    usados |= {m for s in partes.values() for m in s}
    efl = dict(ef)
    for m in sorted(usados):
        if efl.get(m) is None or pd.isna(efl.get(m)):
            efl[m] = 0.0
            avisos.append(f"I34: material {m} sem fator na lista; reposicao contada como "
                          "dado ausente (0), nao como emissao zero")
    ghg_grupo = {g: life_stages.group_ghg(c10, g) for g in ("Iaux", "Iprinc")}
    rep = maintenance.replacements(
        itens, life_km=options.life_km, mode=options.maintenance_mode, part_shares=partes,
        ef=efl, fluid_mass=massa_fluido, group_ghg=ghg_grupo, active=options.active)

    massa = {g: float(c02.loc[c02["IDGG"] == g, "FinalMassKg"].sum())
             for g in ("Iaux", "Iprinc", "K")}
    glider = endoflife.glider_mass(float(c02["FinalMassKg"].sum()),
                                   aux_battery_kg=massa["Iaux"],
                                   traction_battery_kg=massa["Iprinc"], fluids_kg=massa["K"])
    kwh = float(res["gc"].get(IDVP_ENERGY_BATTERY, 0.0) or 0.0)
    fator_veic = ef.get("100")
    fim = endoflife.end_of_life(
        options.eol_method, glider_mass_kg=glider, battery_kwh=kwh,
        factor_glider=options.factor_glider, factor_battery=options.factor_battery,
        factor_vehicle=None if fator_veic is None or pd.isna(fator_veic) else float(fator_veic))

    adj = float(c02["CalibrationKg"].sum())
    declarada = options.declared_mass_kg
    mc = res.get("mass_calibration", {})
    c34 = mass_calibration.validation_row(
        c02, declared_kg=declarada, adjustment_kg=adj,
        s=mc.get("BodyShare") if abs(adj) > 0 else None,
        mass_basis="Declared" if declarada is not None else "Estimated",
        declared_source=options.declared_source)

    etapas = life_stages.build(
        c10=c10, assembly_kg=float(res["totals"]["GHGAssembly"]), replacements=rep, eol=fim,
        include_assembly=boundary == "MAT_ASM")
    c15 = pd.DataFrame(rep["events"], columns=["IDMI", "EventIndex", "EventKm", "GHGkg"])
    return {"C15": c15, "C16": pd.DataFrame([fim]), "C34": pd.DataFrame([c34]),
            "C35": pd.DataFrame(etapas), "warnings": avisos,
            "totals": life_stages.totals(etapas)}


# --------------------------------------------------------------------------
# BLOCO B1R3 -- gravar
#   Apaga e regrava as linhas da rodada para o caso; pode ser repetido.
# --------------------------------------------------------------------------
def write_db(conn, run_id: str, *, ida: int, idcase: int, idv: int, idea: int,
             frames: dict) -> None:
    for t in ("C15_Replacement", "C16_EndOfLife", "C34_MassValidation",
              "C35_VehicleLifeStage"):
        conn.execute(f"DELETE FROM {t} WHERE RunID = ? AND IDCase = ?", (run_id, idcase))
    for r in frames["C15"].itertuples(index=False):
        conn.execute("INSERT INTO C15_Replacement (RunID, IDA, IDCase, IDMI, EventIndex, "
                     "EventKm, GHGkg) VALUES (?,?,?,?,?,?,?)",
                     (run_id, ida, idcase, r.IDMI, int(r.EventIndex), float(r.EventKm),
                      float(r.GHGkg)))
    f = frames["C16"].iloc[0]
    conn.execute("INSERT INTO C16_EndOfLife (RunID, IDA, IDCase, EoLMethod, GliderMassKg, "
                 "BatteryKWh, FactorGlider, FactorBattery, FactorVehicle, GHGEoL) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (run_id, ida, idcase, f["EoLMethod"], f["GliderMassKg"], f["BatteryKWh"],
                  f["FactorGlider"], f["FactorBattery"],
                  None if pd.isna(f["FactorVehicle"]) else f["FactorVehicle"], f["GHGEoL"]))
    m = frames["C34"].iloc[0]

    def nul(x):
        return None if x is None or pd.isna(x) else float(x)
    conn.execute("INSERT INTO C34_MassValidation (RunID, IDA, IDCase, IDV, IDEA, MassBasis, "
                 "DeclaredMassKg, CalculatedMassKg, DiffKg, DiffPct, AdjustmentKg, ResidualKg, "
                 "DeclaredSource, BodyShare, BodyChassisMassBefore, BodyChassisMassAfter) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (run_id, ida, idcase, idv, idea, m["MassBasis"], nul(m["DeclaredMassKg"]),
                  float(m["CalculatedMassKg"]), nul(m["DiffKg"]), nul(m["DiffPct"]),
                  float(m["AdjustmentKg"]), nul(m["ResidualKg"]), m["DeclaredSource"],
                  nul(m["BodyShare"]), nul(m["BodyChassisMassBefore"]),
                  nul(m["BodyChassisMassAfter"])))
    for r in frames["C35"].itertuples(index=False):
        conn.execute("INSERT INTO C35_VehicleLifeStage (RunID, IDA, IDCase, IDV, Stage, "
                     "SubStage, GHGkg, SourceCell, Method, Note) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (run_id, ida, idcase, idv, r.Stage, r.SubStage, float(r.GHGkg),
                      r.SourceCell, r.Method, r.Note))
