"""Vida do veiculo por estagio (T18): a soma dos estagios e o T511 da planilha."""

from __future__ import annotations

import json
import os
import re
import sqlite3

import pandas as pd
import pytest

from core import endoflife as eol
from core import life_stages as ls
from core import maintenance as mt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
REF = os.path.join(REPO, "tests", "fixtures", "b1_reference.json")


def _c10(r):
    """C10 sintetico a partir das linhas da planilha: T516 e o resto por grupo."""
    return pd.DataFrame({"IDGG": ["A", "Iaux", "Iprinc", "K"],
                         "GHGIDGG": [r["516"], r["560"], r["571"], r["617"]]})


def test_estagios_somam_t511_nas_colunas_que_seguem_o_seletor():
    with open(REF, encoding="utf-8") as fh:
        cols = json.load(fh)["m2_columns"]
    n = 0
    for col, d in cols.items():
        r = d["rows"]
        base = r["496"] + r["499"] + r["501"]
        if not (abs(r["495"] - base) < 1e-6 or abs(r["495"] - base - r["500"]) < 1e-6):
            continue                                  # formula antiga (B1-DIV-02)
        # reposicoes e fim de vida como a planilha os tem (modo da coluna e T509)
        repl = {"components": {"tires": r["496"], "aux_battery": r["499"],
                               "traction_battery": r["500"] if abs(r["495"] - base) > 1e-6 else 0.0,
                               "fluids": r["501"]}}
        fim = {"EoLMethod": "AGGREGATE_VEHICLE", "GHGEoL": r["509"]}
        rows = ls.build(c10=_c10(r), assembly_kg=r["510"], replacements=repl, eol=fim)
        assert ls.totals(rows)["TOTAL"] == pytest.approx(r["511"], rel=1e-9), col
        n += 1
    assert n >= 70


def test_producao_inicial_e_o_berco_ao_portao_de_hoje():
    c10 = pd.DataFrame({"IDGG": ["A", "B", "Iaux", "K"], "GHGIDGG": [1000.0, 500.0, 20.0, 90.0]})
    rows = ls.build(c10=c10, assembly_kg=227.0, replacements=None, eol=None)
    t = ls.totals(rows)
    assert t["INITIAL_PRODUCTION"] == pytest.approx(1000 + 500 + 20 + 90 + 227)
    assert t["LIFETIME_REPLACEMENTS"] == 0 and t["END_OF_LIFE"] == 0
    fora = ls.build(c10=c10, assembly_kg=227.0, replacements=None, eol=None,
                    include_assembly=False)
    assert ls.totals(fora)["INITIAL_PRODUCTION"] == pytest.approx(1610.0)


def test_estagio_de_reposicao_e_fim_de_vida_vem_dos_modulos():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    items = [dict(zip([d[0] for d in c.execute("SELECT * FROM P31_MaintenanceItem").description], r))
             for r in c.execute("SELECT * FROM P31_MaintenanceItem")]
    shares: dict = {}
    for i, m, s in c.execute("SELECT IDMI, IDM, Share FROM P31b_MaintenancePartShare"):
        shares.setdefault(i, {})[m] = s
    ef = dict(c.execute("SELECT IDM, EF FROM P11_EmissionFactor WHERE IDEFV='BR23' "
                        "AND EF IS NOT NULL"))
    c.close()
    rep = mt.replacements(items, life_km=200000, mode="Sim Bat", part_shares=shares, ef=ef,
                          fluid_mass={"77": 2.0}, group_ghg={"Iaux": 20.0, "Iprinc": 800.0})
    fim = eol.end_of_life("GLIDER_BATTERY", glider_mass_kg=1000, battery_kwh=40,
                          factor_glider=0.2, factor_battery=20, factor_vehicle=None)
    c10 = pd.DataFrame({"IDGG": ["A"], "GHGIDGG": [1000.0]})
    rows = ls.build(c10=c10, assembly_kg=0.0, replacements=rep, eol=fim)
    t = ls.totals(rows)
    assert t["LIFETIME_REPLACEMENTS"] == pytest.approx(rep["total"])
    assert t["END_OF_LIFE"] == pytest.approx(1000)
    assert {r["Stage"] for r in rows} == set(ls.STAGES)
    assert re.fullmatch(r"M2 T\d+", rows[0]["SourceCell"])


def test_producao_inicial_iguala_o_berco_ao_portao_do_calculo(base):
    """C35 nao muda o resultado de hoje: producao inicial = GHGCradleToGate (MAT_ASM)."""
    from core import calc
    cen = base["D02"].iloc[0]
    idv = int(cen["IDV"])
    rows = base["D03"][base["D03"]["IDV"] == idv]
    gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
    supplied = {int(r["IDVP"]) for _, r in rows.iterrows() if not int(r["IsCalculated"] or 0)}
    hit = rows[rows["IDVP"] == 32]
    bid = hit.iloc[0]["GCText"] if len(hit) else None
    veic = base["D01"].set_index("IDV").loc[idv]
    res = calc.calculate_vehicle(
        base, gc, powertrain=veic["IDVPT"], battery_id=bid, idmpv=int(cen["IDMPV"]),
        idvmr=cen["IDVMR"], idefv=cen["IDEFV"], idapv=cen["IDAPV"], boundary="MAT_ASM",
        supplied=supplied)
    linhas = ls.build(c10=res["C10"], assembly_kg=res["totals"]["GHGAssembly"],
                      replacements=None, eol=None)
    assert ls.totals(linhas)["INITIAL_PRODUCTION"] == pytest.approx(
        res["totals"]["GHGCradleToGate"], rel=1e-9)
