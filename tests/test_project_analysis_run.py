"""Projeto, analise, rodada e regras I16 a I23 (Fase A, passo 4)."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import analysis, project, run, validate

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
CFG = dict(fuel="BR23", norm="NBR", curve="Default", idefv="BR23", idmpv=1, idapv="A-EF")


@pytest.fixture
def proj(tmp_path):
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    project.create(conn, "Teste")
    yield conn, path
    conn.close()


def _cfg(conn):
    row = conn.execute("SELECT IDEFV FROM P10_EFVersion ORDER BY IDEFV LIMIT 1").fetchone()
    apv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion LIMIT 1").fetchone()[0]
    cfg = dict(CFG, idefv=row[0], idapv=apv)
    cfg["fuel"], cfg["norm"], cfg["curve"] = _defaults(conn)
    return cfg


def _defaults(conn):
    cols = {r[1]: r for r in conn.execute("PRAGMA table_info(D06_Analysis)")}
    return ("E27", "NBR", "Default") if cols else (None, None, None)


def test_identity_and_modes(proj):
    conn, path = proj
    assert project.mode(conn) == project.EDIT
    assert project.mode(conn, selected_count=2) == project.READ
    conn.execute("UPDATE M03_Project SET IsExample = 1")
    assert project.mode(conn) == project.READ
    assert project.read_only_reason(conn)


def test_save_as_makes_new_identity(proj, tmp_path):
    conn, _ = proj
    old = project.identity(conn)["ProjectID"]
    conn.commit()
    new = project.save_as(conn, str(tmp_path / "c.sqlite"), "Copia")
    c2 = sqlite3.connect(str(tmp_path / "c.sqlite"))
    ident = project.identity(c2)
    assert ident["ProjectID"] == new != old
    assert ident["CopiedFromProjectID"] == old and not ident["IsExample"]


def test_recipes_follow_powertrain(proj):
    conn, _ = proj
    hev = analysis.recipes_for(conn, "HEV")
    assert hev and analysis.recipes_for(conn, "SHEV") == hev


def test_ec_has_six_cases_and_passes_rules(proj):
    conn, _ = proj
    ida = analysis.create_ec(conn, "EC", "A0", _cfg(conn))
    assert validate.check_analysis(conn, ida) == []
    rows = conn.execute("SELECT CaseRole, SizingOrigin FROM D07_AnalysisVehicle "
                        "WHERE IDA = ? ORDER BY IDCase", (ida,)).fetchall()
    assert [r[0] for r in rows] == ["REF"] + ["EQ"] * 5
    assert {r[1] for r in rows} == {"ExcelReference"}


def test_ec_with_other_reference_leaves_pending(proj):
    conn, _ = proj
    sel = conn.execute("SELECT IDMVSelecao FROM P29_VehicleCategory WHERE IDVC='A0'").fetchone()[0]
    other = conn.execute("SELECT IDMV FROM P26_MarketVehicle WHERE IDVPT='ICEV' AND IDMV<>? "
                         "AND MarketGroup = (SELECT MarketGroup FROM P29_VehicleCategory "
                         "WHERE IDVC='A0') LIMIT 1", (sel,)).fetchone()[0]
    ida = analysis.create_ec(conn, "EC2", "A0", _cfg(conn), idmv_ref=other)
    origins = [r[0] for r in conn.execute("SELECT SizingOrigin FROM D07_AnalysisVehicle "
                                          "WHERE IDA = ? ORDER BY IDCase", (ida,))]
    assert origins[0] == "Manufacturer" and set(origins[1:]) == {"Pending"}
    assert validate.check_analysis(conn, ida) == []


def test_fc_limits(proj):
    conn, _ = proj
    mv = conn.execute("SELECT IDMV FROM P26_MarketVehicle WHERE IDVPT='ICEV' LIMIT 1").fetchone()[0]
    with pytest.raises(ValueError):
        analysis.create_fc(conn, "FC", _cfg(conn), [], max_cases=3)
    with pytest.raises(ValueError):
        analysis.create_fc(conn, "FC", _cfg(conn), [{"idmv": mv}] * 4, max_cases=3)
    ida = analysis.create_fc(conn, "FC", _cfg(conn), [{"idmv": mv}], max_cases=3)
    assert validate.check_analysis(conn, ida) == []


def test_rules_catch_violations(proj):
    conn, _ = proj
    ida = analysis.create_ec(conn, "EC", "A0", _cfg(conn))
    conn.execute("UPDATE D02_EvaluationAlternative SET Boundary = 'MAT' WHERE IDV = "
                 "(SELECT IDV FROM D07_AnalysisVehicle WHERE IDA = ? AND IDCase = 2)", (ida,))
    conn.execute("INSERT INTO D12_CombinedPowerOverride (IDA, IDCase, FactorICE, FactorEE) "
                 "VALUES (?, 1, 1, 1)", (ida,))
    msgs = " ".join(validate.check_analysis(conn, ida))
    assert "I19" in msgs and "I22" in msgs


def test_freeze_execute_is_reproducible(proj):
    conn, path = proj
    ida = analysis.create_ec(conn, "EC", "A0", _cfg(conn))
    ids = []
    for _ in range(2):
        rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
        run.execute(conn, path, rid)
        ids.append(rid)
    a, b = ids
    h = [conn.execute("SELECT InputHash FROM D09_Run WHERE RunID=?", (r,)).fetchone()[0]
         for r in ids]
    assert h[0] == h[1]
    q = "SELECT CaseKey, IDInd, Value, ValueText, ValueOrigin FROM R45_PowertrainSummary " \
        "WHERE RunID = ? ORDER BY CaseKey, IDInd"
    ra, rb = conn.execute(q, (a,)).fetchall(), conn.execute(q, (b,)).fetchall()
    assert ra and ra == rb
    assert validate.check_run_origin(conn, a) == []
    assert {r[4] for r in ra} <= {"Calculated", "ExcelReference", "Preview"}


def test_rename_e_summary(proj):
    conn, _ = proj
    ident = project.identity(conn)
    assert project.summary(conn)["Mode"] is None
    project.rename(conn, "  Novo nome  ")
    after = project.identity(conn)
    assert after["ProjectName"] == "Novo nome" and after["ProjectID"] == ident["ProjectID"]
    with pytest.raises(ValueError):
        project.rename(conn, "   ")
    analysis.create_ec(conn, "EC", "A0", _cfg(conn))
    assert project.summary(conn)["Mode"] == "EC"
