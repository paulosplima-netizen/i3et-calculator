"""Massa declarada efetiva e calibracao automatica (T38; decisao de 20/11/2026).

Parametro 25 informado = massa conhecida (veiculo de mercado); calculado = veiculo teorico,
sem rateio. Regra em core/b1_choices.mass_basis; efeito na rodada em core/calc.py.
"""

from __future__ import annotations

import shutil
import sqlite3

import pytest

from core import analysis, b1_choices as ch, project, run
from tests.test_project_analysis_run import DB, _cfg

KNOWN = [{"IDVP": 25, "GC": 1200.0, "IsCalculated": 0}]
CALC = [{"IDVP": 25, "GC": 1200.0, "IsCalculated": 1}]


def test_mercado_usa_o_parametro_25():
    mb = ch.mass_basis({"SizingOrigin": "Manufacturer"}, KNOWN)
    assert (mb["declared_kg"], mb["basis"], mb["auto"]) == (1200.0, ch.BASIS_MARKET, True)
    assert mb["source"] == ch.SOURCE_PARAM25


def test_teorico_nao_tem_massa_declarada_nem_rateio():
    mb = ch.mass_basis({"SizingOrigin": "Calculated"}, CALC)
    assert (mb["declared_kg"], mb["basis"], mb["auto"]) == (None, ch.BASIS_ITERATIVE, False)
    # mesmo com a origem "Manufacturer", parametro 25 calculado nao e massa conhecida
    mb = ch.mass_basis({"SizingOrigin": "Manufacturer"}, CALC)
    assert mb["declared_kg"] is None and not mb["auto"]


def test_excel_reference_fica_desligado_ate_ligar():
    case = {"SizingOrigin": "ExcelReference"}
    mb = ch.mass_basis(case, KNOWN)
    assert mb["declared_kg"] is None and not mb["auto"] and mb["basis"] == ch.BASIS_ESTIMATED
    mb = ch.mass_basis(dict(case, MassCalibrationMode="ON"), KNOWN)
    assert mb["declared_kg"] == 1200.0 and mb["auto"]


def test_digitada_prevalece_e_off_desliga():
    case = {"SizingOrigin": "Manufacturer", "DeclaredMassKg": 1300.0, "DeclaredSource": "ficha"}
    mb = ch.mass_basis(case, KNOWN)
    assert (mb["declared_kg"], mb["basis"], mb["source"]) == (1300.0, ch.BASIS_TYPED, "ficha")
    mb = ch.mass_basis(dict(case, MassCalibrationMode="OFF"), KNOWN)
    assert mb["declared_kg"] == 1300.0 and not mb["auto"]
    # digitada em veiculo teorico: so informativa, a menos que se ligue
    mb = ch.mass_basis({"SizingOrigin": "Calculated", "DeclaredMassKg": 1300.0}, CALC)
    assert mb["declared_kg"] == 1300.0 and not mb["auto"]


@pytest.fixture
def proj(tmp_path):
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    project.create(conn, "Teste")
    ida = analysis.create_ec(conn, "EC", "A0", _cfg(conn))
    yield conn, path, ida
    conn.close()


def _rodar(conn, path, ida):
    rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
    run.execute(conn, path, rid)
    return {r[0]: r for r in conn.execute(
        "SELECT IDCase, MassBasis, DeclaredMassKg, CalculatedMassKg, AdjustmentKg, ResidualKg, "
        "DeclaredSource FROM C34_MassValidation WHERE RunID = ?", (rid,))}


def _mercado(conn, idcase=1, massa=1100.0):
    idv = conn.execute("SELECT IDV FROM D07_AnalysisVehicle WHERE IDCase = ?",
                       (idcase,)).fetchone()[0]
    conn.execute("UPDATE D07_AnalysisVehicle SET SizingOrigin = 'Manufacturer' "
                 "WHERE IDCase = ?", (idcase,))
    conn.execute("UPDATE D03_VehicleParamValue SET GC = ?, IsCalculated = 0 "
                 "WHERE IDV = ? AND IDVP = 25", (massa, idv))
    conn.commit()


def test_rodada_teorica_nao_rateia(proj):
    conn, path, ida = proj
    r = _rodar(conn, path, ida)
    assert all(v[1] == ch.BASIS_ITERATIVE and v[2] is None and v[4] == 0 for v in r.values())


def test_rodada_de_mercado_calibra_sozinha(proj):
    conn, path, ida = proj
    _mercado(conn)
    r = _rodar(conn, path, ida)[1]
    assert r[1] == ch.BASIS_MARKET and r[2] == pytest.approx(1100.0)
    assert r[6] == ch.SOURCE_PARAM25
    assert r[4] == pytest.approx(r[2] - r[3])                 # ajuste = declarada - estimada
    assert r[5] == pytest.approx(0.0, abs=1e-6)               # massa final = declarada
    # os demais casos, teoricos, seguem sem rateio
    assert all(v[4] == 0 for k, v in _rodar(conn, path, ida).items() if k != 1)


def test_modo_off_desliga_e_ajuste_manual_prevalece(proj):
    conn, path, ida = proj
    _mercado(conn)
    conn.execute("UPDATE D07_AnalysisVehicle SET MassCalibrationMode = 'OFF' WHERE IDCase = 1")
    conn.commit()
    r = _rodar(conn, path, ida)[1]
    assert r[1] == ch.BASIS_MARKET and r[4] == 0 and r[5] == pytest.approx(r[2] - r[3])
    conn.execute("UPDATE D07_AnalysisVehicle SET MassCalibrationMode = NULL, "
                 "MassAdjustmentKg = 5 WHERE IDCase = 1")
    conn.commit()
    assert _rodar(conn, path, ida)[1][4] == pytest.approx(5.0)
