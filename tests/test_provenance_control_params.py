"""Selo de origem (core/provenance.py) e valor efetivo (core/control_params.py)."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile

import pytest

from core import control_params as cp
from core import provenance as pv

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture()
def conn():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "b.sqlite")
    shutil.copy(BASE, path)
    c = sqlite3.connect(path)
    c.execute("PRAGMA foreign_keys=OFF")
    yield c
    c.close()
    shutil.rmtree(d, ignore_errors=True)


def test_selo_calculado_vale_em_qualquer_caso():
    s = pv.classify("Calculated", is_recorded_case=False, has_reference=False)
    assert s.origin == pv.CALCULATED and pv.label(s, 3) == "Calculated (run S3)"


def test_selo_excel_so_para_configuracao_gravada_com_referencia():
    assert pv.classify("ExcelReference", is_recorded_case=True, has_reference=True).origin \
        == pv.EXCEL_REFERENCE
    for rec, ref in ((False, True), (True, False)):
        s = pv.classify("ExcelReference", is_recorded_case=rec, has_reference=ref)
        assert s.origin is None and s.note == pv.NOT_AVAILABLE


def test_previa_nao_entra_em_relatorio():
    s = pv.classify("Calculated", is_recorded_case=True, has_reference=True, is_preview=True)
    assert s.origin == pv.PREVIEW and not pv.allowed_in_report(s)
    assert pv.allowed_in_report(pv.Seal(pv.CALCULATED))


def test_selo_recusa_status_desconhecido():
    with pytest.raises(ValueError):
        pv.classify("Foo", is_recorded_case=True, has_reference=True)


def test_valor_efetivo_padrao_e_igual_nos_tres_perfis(conn):
    vals = [cp.effective_values(conn, 1, p) for p in cp.PROFILES]
    assert len(vals[0]) == 205
    assert vals[0] == vals[1] == vals[2]          # BasicValue nao e usado


def test_alteracao_vale_so_no_perfil_e_na_analise(conn):
    idcp = conn.execute("SELECT IDCP FROM P30_ControlParam WHERE IsCalculated = 0 "
                        "AND DefaultValue IS NOT NULL AND MinValue IS NOT NULL "
                        "AND MaxValue IS NOT NULL AND MinValue <= MaxValue LIMIT 1").fetchone()[0]
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(
        "INSERT OR IGNORE INTO D06_Analysis (IDA, DsA, Mode, AnalysisType, FuelScenario, "
        "TestNorm, DistanceCurve, IDEFV, IDMPV, IDAPV, Boundary, SPHEVEco, "
        "LightweightingOn, ParamProfile, CombinedPowerRule) "
        "VALUES (1,'t','FC','GHG_LCA_LCC','x','NBR','c','G22',1,'a','MAT_ASM',0,0,"
        "'Expert','Default')")
    hi = conn.execute("SELECT MaxValue FROM P30_ControlParam WHERE IDCP=?", (idcp,)).fetchone()[0]
    fora = cp.set_value(conn, 1, idcp, "Expert", value=hi + 1.0, source="teste")
    assert fora is True
    e = cp.effective_values(conn, 1, "Expert")[idcp]
    assert e.source == "User" and e.out_of_range
    assert cp.effective_values(conn, 1, "Basic")[idcp].source == "Default"
    assert cp.effective_values(conn, 2, "Expert")[idcp].source == "Default"
    assert cp.restore(conn, 1, idcp, "Expert") is True
    assert cp.effective_values(conn, 1, "Expert")[idcp].source == "Default"
    assert cp.restore(conn, 1, idcp, "Expert") is False


def test_recusas(conn):
    q = "SELECT IDCP FROM P30_ControlParam WHERE IsCalculated = ? LIMIT 1"
    calc = conn.execute(q, (1,)).fetchone()[0]
    livre = conn.execute(q, (0,)).fetchone()[0]
    with pytest.raises(ValueError):
        cp.set_value(conn, 1, calc, "Expert", value=1.0, source="x")        # I20
    with pytest.raises(ValueError):
        cp.set_value(conn, 1, livre, "Expert", value=1.0, source="  ")      # I27
    with pytest.raises(ValueError):
        cp.set_value(conn, 1, livre, "Expert", value=1.0, text="a", source="x")
    with pytest.raises(KeyError):
        cp.set_value(conn, 1, "ZZZ", "Expert", value=1.0, source="x")
    with pytest.raises(ValueError):
        cp.effective_values(conn, 1, "Foo")


def test_faixa_invertida_ou_ausente_nunca_acusa():
    assert not cp.is_out_of_range(5.0, 10.0, 1.0)
    assert not cp.is_out_of_range(5.0, None, 10.0)
    assert cp.is_out_of_range(11.0, 0.0, 10.0) and not cp.is_out_of_range(10.0, 0.0, 10.0)
