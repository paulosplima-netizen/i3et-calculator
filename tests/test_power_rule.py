"""Potencia combinada por fatores de uso dos motores (core/power_rule.py)."""

from __future__ import annotations

import os
import sqlite3

import pandas as pd
import pytest

from core import params, power_rule, schema

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{BASE}?mode=ro", uri=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def tabelas(conn):
    return power_rule.load_defaults(conn), power_rule.load_fits(conn)


def test_pares_fixos_nao_dependem_da_regra_nem_do_caso(tabelas):
    defaults, fits = tabelas
    for pt, par in (("ICEV", (1, 0)), ("BEV", (0, 1)), ("SHEV", (0, 1)), ("SPHEV", (0, 1))):
        for regra in power_rule.RULES:
            f = power_rule.effective_factors(pt, rule=regra, case_key="A04",
                                             defaults=defaults, fits=fits)
            assert (f.ice, f.ee) == par and not f.provisional


def test_padrao_de_hev_e_phev_e_a_soma_provisoria(tabelas):
    defaults, _ = tabelas
    for pt in ("HEV", "PHEV"):
        f = power_rule.effective_factors(pt, defaults=defaults)
        assert (f.ice, f.ee, f.provisional, f.origin) == (1.0, 1.0, True, "Default")
        assert f.combine(90.0, 40.0) == 130.0


def test_excel_parity_usa_o_par_arbitrado_do_caso(tabelas):
    defaults, fits = tabelas
    f = power_rule.effective_factors("HEV", rule="ExcelParity", case_key="A02",
                                     defaults=defaults, fits=fits)
    assert (f.ice, f.ee, f.origin) == (1.0, 0.0, "ExcelFit")
    # sem par arbitrado, volta ao padrao
    g = power_rule.effective_factors("HEV", rule="ExcelParity", case_key="ZZ9",
                                     defaults=defaults, fits=fits)
    assert g.origin == "Default"


def test_excel_parity_reproduz_as_dez_potencias_gravadas(conn, tabelas):
    """Control Panel BP12:BU12 e BF12:BI12."""
    defaults, fits = tabelas
    linhas = conn.execute("SELECT CaseKey, IDVPT, PowerICE, PowerEE, PowerCombined "
                          "FROM P56_CombinedPowerFit WHERE RefSet LIKE 'CP_OUT%'").fetchall()
    assert len(linhas) == 10
    for caso, pt, ice, ee, comb in linhas:
        p = power_rule.combined_power(pt, ice, ee, rule="ExcelParity", case_key=caso,
                                      defaults=defaults, fits=fits)
        assert p == pytest.approx(comb, rel=1e-9), caso


def test_ajuste_do_usuario_prevalece_e_so_vale_para_hev_e_phev(tabelas):
    defaults, fits = tabelas
    ajuste = {2: power_rule.Factors(1.0, 0.4, "UserOverride", False)}
    f = power_rule.effective_factors("HEV", rule="ExcelParity", case_key="A02", idcase=2,
                                     defaults=defaults, fits=fits, overrides=ajuste)
    assert (f.ice, f.ee, f.origin) == (1.0, 0.4, "UserOverride")
    outro = power_rule.effective_factors("BEV", idcase=2, defaults=defaults, overrides=ajuste)
    assert (outro.ice, outro.ee) == (0.0, 1.0)


def test_gravar_e_limpar_o_ajuste_em_d12():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = OFF")
    c.executescript(schema.DDL_ANALYSIS_010 if hasattr(schema, "DDL_ANALYSIS_010") else "")
    c.execute("INSERT INTO D06_Analysis (IDA, DsA, Mode, IDVC, IDMVRef, FuelScenario, "
              "TestNorm, DistanceCurve, IDEFV, IDMPV, IDAPV) VALUES "
              "(1, 'a', 'EC', 'A0', 1, 'E100', 'NBR', 'c', 'G24', 1, 'x')")
    for caso, chave, pt in ((1, "A01", "ICEV"), (2, "A02", "HEV")):
        c.execute("INSERT INTO D07_AnalysisVehicle (IDA, IDCase, CaseKey, CaseRole, IDVPT, "
                  "IDV, IDEA, SizingOrigin) VALUES (1, ?, ?, 'EQ', ?, 1, 1, 'Pending')",
                  (caso, chave, pt))
    power_rule.set_override(c, 1, 2, 0.8, 0.5, "teste")
    power_rule.set_override(c, 1, 2, 0.9, 0.2)                   # regrava
    assert power_rule.load_overrides(c, 1)[2].ee == 0.2
    with pytest.raises(ValueError):                              # ICEV e fixo
        power_rule.set_override(c, 1, 1, 0.5, 0.5)
    with pytest.raises(ValueError):                              # fora de 0 a 1
        power_rule.set_override(c, 1, 2, 1.2, 0.5)
    power_rule.clear_override(c, 1, 2)
    assert power_rule.load_overrides(c, 1) == {}


def _gc(ice, ee):
    return {2: ice, 3: ee, 7: 4.0, 8: 1.8, 14: 1.0}


def test_idvp_15_usa_os_fatores_e_sem_eles_mantem_a_regra_da_0_9_0():
    p19 = pd.DataFrame(columns=["IDBMd", "PowerDensity", "EnergyDensity", "RefEnergy"])
    com = params.resolve(_gc(90.0, 40.0), powertrain="HEV", battery_id=None, p19=p19,
                         power_factors=(1.0, 0.5))
    assert com[15] == pytest.approx(110.0)
    sem = params.resolve(_gc(90.0, 40.0), powertrain="HEV", battery_id=None, p19=p19)
    assert sem[15] == 90.0                                       # maior valor, como na 0.9.0
    serie = params.resolve(_gc(90.0, 40.0), powertrain="SHEV", battery_id=None, p19=p19)
    assert serie[15] == 40.0
