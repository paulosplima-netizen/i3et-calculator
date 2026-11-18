"""Fim de vida (T17): metodos, conta manual e paridade do metodo agregado com T509."""

from __future__ import annotations

import json
import os
import sqlite3

import pytest

from core import endoflife as eol

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
REF = os.path.join(REPO, "tests", "fixtures", "b1_reference.json")


def _fe(idm, idefv="BR23"):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return c.execute("SELECT EF FROM P11_EmissionFactor WHERE IDEFV=? AND IDM=?",
                         (idefv, idm)).fetchone()[0]
    finally:
        c.close()


def _kw(**extra):
    base = dict(glider_mass_kg=1200.0, battery_kwh=50.0, factor_glider=0.2,
                factor_battery=20.0, factor_vehicle=177.68)
    base.update(extra)
    return base


def test_metodo_padrao_e_a_conta_manual():
    r = eol.end_of_life("GLIDER_BATTERY", **_kw())
    assert r["GHGEoL"] == pytest.approx(0.2 * 1200 + 20 * 50)


def test_so_o_metodo_escolhido_soma_e_os_fatores_ficam_registrados():
    ag = eol.end_of_life("AGGREGATE_VEHICLE", **_kw())
    ex = eol.end_of_life("EXCLUDED", **_kw())
    assert ag["GHGEoL"] == 177.68 and ex["GHGEoL"] == 0.0
    for r in (ag, ex):
        assert (r["FactorGlider"], r["FactorBattery"], r["FactorVehicle"]) == (0.2, 20.0, 177.68)


def test_entradas_invalidas():
    with pytest.raises(ValueError):
        eol.end_of_life("OUTRO", **_kw())
    with pytest.raises(ValueError):
        eol.end_of_life("GLIDER_BATTERY", **_kw(battery_kwh=-1))
    with pytest.raises(ValueError):
        eol.end_of_life("AGGREGATE_VEHICLE", **_kw(factor_vehicle=None))


def test_glider_nunca_negativo():
    assert eol.glider_mass(1000, traction_battery_kg=150, fluids_kg=40, aux_battery_kg=10) == 800
    assert eol.glider_mass(100, traction_battery_kg=150) == 0


def _cols():
    with open(REF, encoding="utf-8") as fh:
        return json.load(fh)["m2_columns"]


def test_metodo_agregado_reproduz_t509_nas_colunas_do_fator_por_veiculo():
    """T509 = fator por veiculo (IDM 100) nas colunas T:AC, AR:CA (GREET 2022 e 2024)."""
    cols = _cols()
    fator = _fe("100")
    for c in ("T", "AC", "AR", "CA"):
        r = eol.end_of_life("AGGREGATE_VEHICLE", **_kw(factor_vehicle=fator))
        assert r["GHGEoL"] == pytest.approx(cols[c]["rows"]["509"], rel=1e-9), c


def test_metodo_padrao_reproduz_t509_das_colunas_sv1_a_sv4():
    """Nas SV1 a SV4 a planilha ja usa glider x 0,2 + kWh x 20 (FD707 + FD708).

    Com a massa do glider da planilha (linha 662) a conta e exata. A linha 662 soma
    as massas de material, e nas receitas com participacao negativa zerada a soma
    passa um pouco da massa do grupo (divergencia D8 da base: o aplicativo normaliza);
    com a massa por grupo a diferenca e de 0,1% (0,5 a 0,8 kg em 940 a 1450 kg).
    """
    cols = _cols()
    for c in ("FD", "FE", "FF", "FG"):
        r = cols[c]["rows"]
        kw = dict(battery_kwh=r["15"], factor_glider=0.2, factor_battery=20.0,
                  factor_vehicle=None)
        exato = eol.end_of_life("GLIDER_BATTERY", glider_mass_kg=r["662"], **kw)
        assert exato["GHGEoL"] == pytest.approx(r["509"], rel=1e-9), c
        g = eol.glider_mass(r["69"], aux_battery_kg=r["78"], traction_battery_kg=r["79"],
                            fluids_kg=r["81"])
        assert g == pytest.approx(r["662"], rel=2e-3), c
        por_grupo = eol.end_of_life("GLIDER_BATTERY", glider_mass_kg=g, **kw)
        assert por_grupo["GHGEoL"] == pytest.approx(r["509"], rel=2e-3), c


def test_diferenca_do_metodo_padrao_para_a_planilha():
    """Divergencia registrada: padrao - T509 = -177,68 + 0,2 x glider + 20 x kWh."""
    p = eol.end_of_life("GLIDER_BATTERY", **_kw())["GHGEoL"]
    a = eol.end_of_life("AGGREGATE_VEHICLE", **_kw())["GHGEoL"]
    assert p - a == pytest.approx(-177.68 + 0.2 * 1200 + 20 * 50)
