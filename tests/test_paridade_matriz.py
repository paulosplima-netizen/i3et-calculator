"""Matriz de paridade da Fase A (docs/06, secao 9): linhas ainda sem teste proprio.

As linhas T02/T03/T04/T10/T11 estao em test_fixtures_fase_a, test_power_rule e
test_vehicle_defaults; T05/T18 em test_generic_battery; T41 em
test_project_analysis_run. Aqui ficam o que a planilha nao grava (livre escolha
com 7 casos, caso Pending, fatores padrao (1; 1), FCEV) e as relacoes entre elas.
"""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import analysis, project, run, validate

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture
def proj(tmp_path):
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    project.create(conn, "Matriz")
    yield conn, path
    conn.close()


def _cfg(conn, **extra):
    idefv = conn.execute("SELECT IDEFV FROM P10_EFVersion ORDER BY IDEFV LIMIT 1").fetchone()[0]
    apv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion LIMIT 1").fetchone()[0]
    return dict(fuel="E27", norm="NBR", curve="Default", idefv=idefv, idmpv=1, idapv=apv, **extra)


def _go(conn, path, ida):
    rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
    run.execute(conn, path, rid)
    return rid


def _r45(conn, rid, key, ind):
    row = conn.execute("SELECT Value, ValueOrigin FROM R45_PowertrainSummary "
                       "WHERE RunID = ? AND CaseKey = ? AND IDInd = ?", (rid, key, ind)).fetchone()
    return row


def _market(conn, pt, n=1):
    return [r[0] for r in conn.execute(
        "SELECT IDMV FROM P26_MarketVehicle WHERE IDVPT = ? ORDER BY IDMV LIMIT ?", (pt, n))]


def test_fatores_padrao_somam_no_hev_e_no_phev_e_a_paridade_nao(proj):
    """A planilha nao usa (1; 1) no HEV; a regra padrao sim, e provisoriamente."""
    conn, path = proj
    pot = {}
    for rule in ("Default", "ExcelParity"):
        ida = analysis.create_ec(conn, rule, "A0", _cfg(conn, power_rule=rule))
        rid = _go(conn, path, ida)
        pot[rule] = {k: _r45(conn, rid, k, "O12")[0] for k in ("A01", "A02", "A04")}
    assert pot["ExcelParity"]["A01"] == pytest.approx(pot["Default"]["A01"])        # ICEV
    assert pot["Default"]["A02"] > pot["ExcelParity"]["A02"] * 1.3                  # HEV soma
    # PHEV (1; 1) nos dois
    assert pot["Default"]["A04"] == pytest.approx(pot["ExcelParity"]["A04"], rel=1e-9)


def test_livre_escolha_com_sete_casos_roda_e_cada_valor_tem_origem(proj):
    conn, path = proj
    mvs = [_market(conn, pt)[0] for pt in ("ICEV", "HEV", "SHEV", "PHEV", "SPHEV", "BEV")]
    mvs.append(_market(conn, "ICEV", 2)[-1])
    ida = analysis.create_fc(conn, "FC7", _cfg(conn), [{"idmv": m} for m in mvs], max_cases=7)
    assert validate.check_analysis(conn, ida) == []
    rid = _go(conn, path, ida)
    assert validate.check_run_origin(conn, rid) == []
    for n in range(1, 8):
        mass = _r45(conn, rid, f"SV{n}", "O20")
        assert mass is not None and mass[0] > 500, n
        assert mass[1] in {"Calculated", "ExcelReference", "Preview"}


def test_caso_pending_nao_recebe_valor_calculado_de_outra_rodada(proj):
    conn, path = proj
    sel = conn.execute("SELECT IDMVSelecao FROM P29_VehicleCategory WHERE IDVC='A0'").fetchone()[0]
    other = conn.execute(
        "SELECT IDMV FROM P26_MarketVehicle WHERE IDVPT='ICEV' AND IDMV<>? AND MarketGroup = "
        "(SELECT MarketGroup FROM P29_VehicleCategory WHERE IDVC='A0') LIMIT 1",
        (sel,)).fetchone()[0]
    ida = analysis.create_ec(conn, "Pend", "A0", _cfg(conn), idmv_ref=other)
    rid = _go(conn, path, ida)
    assert validate.check_run_origin(conn, rid) == []
    pend = [r[0] for r in conn.execute(
        "SELECT CaseKey FROM D07_AnalysisVehicle WHERE IDA = ? "
        "AND SizingOrigin = 'Pending'", (ida,))]
    assert len(pend) == 5
    for key in pend:
        row = _r45(conn, rid, key, "O29")
        assert row is None or row[1] != "Calculated"


def test_fcev_fica_fora_da_comparacao_equalizada():
    assert "FCEV" not in analysis.EC_ORDER


def test_mesma_entrada_mesmo_resultado_em_projetos_distintos(proj, tmp_path):
    """T41: InputHash igual implica R45 igual, tambem entre duas copias do projeto."""
    conn, path = proj
    ida = analysis.create_ec(conn, "EC", "A0", _cfg(conn))
    rid = _go(conn, path, ida)
    other = str(tmp_path / "q.sqlite")
    shutil.copy(DB, other)
    c2 = sqlite3.connect(other)
    project.create(c2, "Outro")
    ida2 = analysis.create_ec(c2, "EC", "A0", _cfg(c2))
    rid2 = _go(c2, other, ida2)
    h1 = conn.execute("SELECT InputHash FROM D09_Run WHERE RunID=?", (rid,)).fetchone()[0]
    h2 = c2.execute("SELECT InputHash FROM D09_Run WHERE RunID=?", (rid2,)).fetchone()[0]
    q = "SELECT CaseKey, IDInd, Value FROM R45_PowertrainSummary WHERE RunID=? ORDER BY 1,2"
    if h1 == h2:
        assert conn.execute(q, (rid,)).fetchall() == c2.execute(q, (rid2,)).fetchall()
    else:                                                       # o hash inclui o nome do projeto
        a = [r[1:] for r in conn.execute(q, (rid,))]
        b = [r[1:] for r in c2.execute(q, (rid2,))]
        assert a == b
    c2.close()
