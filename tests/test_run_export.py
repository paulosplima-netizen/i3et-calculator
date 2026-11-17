"""Exportacao de rodadas e do projeto em JSON (Fase A, passo 6)."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3

import pytest

from core import analysis, project, run, run_export

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def done(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("exp") / "p.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    pid = project.create(conn, "Exporta")
    idefv = conn.execute("SELECT IDEFV FROM P10_EFVersion ORDER BY IDEFV LIMIT 1").fetchone()[0]
    apv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion LIMIT 1").fetchone()[0]
    cfg = dict(fuel="E27", norm="NBR", curve="Default", idefv=idefv, idmpv=1, idapv=apv)
    ida = analysis.create_ec(conn, "EC", "A0", cfg)
    rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
    run.execute(conn, path, rid)
    yield conn, pid, rid
    conn.close()


def test_run_export_carries_identity_hashes_and_seals(done):
    conn, pid, rid = done
    out = run_export.export_run(conn, rid)
    assert out["project"]["ProjectID"] == pid
    assert out["run"]["RunID"] == rid and len(out["run"]["InputHash"]) == 64
    assert out["run"]["ParamBaseHash"]
    assert out["results"] and all(r["Seal"] for r in out["results"])
    assert {r["ValueOrigin"] for r in out["results"]} <= {"Calculated", "ExcelReference"}
    assert run_export.verify(out) == []


def test_previews_never_leave(done):
    conn, _, rid = done
    conn.execute("UPDATE R45_PowertrainSummary SET ValueOrigin = 'Preview' "
                 "WHERE RunID = ? AND CaseKey = 'A01' AND IDInd = 'O29'", (rid,))
    try:
        out = run_export.export_run(conn, rid)
        assert out["omitted_previews"] == 1
        assert not [r for r in out["results"] if r["CaseKey"] == "A01" and r["IDInd"] == "O29"]
    finally:
        conn.execute("UPDATE R45_PowertrainSummary SET ValueOrigin = 'Calculated' "
                     "WHERE RunID = ? AND CaseKey = 'A01' AND IDInd = 'O29'", (rid,))


def test_project_export_has_configuration_vehicles_and_runs(done):
    conn, pid, rid = done
    out = run_export.export_project(conn)
    assert out["project"]["ProjectID"] == pid
    assert len(out["configuration"]["D07_AnalysisVehicle"]) == 6
    assert len(out["vehicles"]["D01_Vehicle"]) >= 6
    assert [r["run"]["RunID"] for r in out["runs"]] == [rid]
    assert run_export.verify(out) == []


def test_file_round_trip_and_tamper_detection(done, tmp_path):
    conn, _, rid = done
    out = run_export.export_run(conn, rid)
    path = run_export.write(out, str(tmp_path / "r.json"))
    back = json.load(open(path, encoding="utf-8"))
    assert back == out and run_export.verify(back) == []
    back["results"][0]["Value"] = (back["results"][0]["Value"] or 0) + 1
    assert any("ExportHash" in p for p in run_export.verify(back))


def test_same_run_exports_the_same_bytes(done):
    conn, _, rid = done
    a = run_export.canonical(run_export.export_run(conn, rid))
    b = run_export.canonical(run_export.export_run(conn, rid))
    assert a == b


def test_not_a_project_is_refused(tmp_path):
    path = str(tmp_path / "x.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    with pytest.raises(ValueError):
        run_export.export_project(conn)
    conn.close()


def test_r46_puts_runs_side_by_side(done):
    conn, _, rid = done
    rows = conn.execute("SELECT RunSeq, InputHash, ParamBaseHash, DsInd, ValueOrigin "
                        "FROM R46_RunComparison WHERE RunID = ?", (rid,)).fetchall()
    assert rows and all(r[1] and r[2] and r[3] for r in rows)
    assert len(rows) == conn.execute("SELECT COUNT(*) FROM R45_PowertrainSummary "
                                     "WHERE RunID = ?", (rid,)).fetchone()[0]


def test_cli_writes_project_and_run_files(done, tmp_path):
    from tools import export_run as cli
    conn, _, rid = done
    path = conn.execute("PRAGMA database_list").fetchone()[2]
    conn.commit()
    assert cli.main([path, "--saida", str(tmp_path / "p.json")]) == 0
    assert cli.main([path, "--run", rid, "--saida", str(tmp_path / "r.json")]) == 0
    assert json.load(open(tmp_path / "r.json", encoding="utf-8"))["kind"] == "run"
