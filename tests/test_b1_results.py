"""Saidas do B1: C15, C16, C34, C35 de um caso real e a gravacao no banco."""

from __future__ import annotations

import os
import sqlite3

import pandas as pd
import pytest

from core import b1_results as b1
from core import calc
from core.loader import effective_emission_factors, load_sqlite

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def caso():
    base = load_sqlite(DB)
    cen = base["D02"].iloc[0]
    idv = int(cen["IDV"])
    rows = base["D03"][base["D03"]["IDV"] == idv]
    gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
    supplied = {int(r["IDVP"]) for _, r in rows.iterrows() if not int(r["IsCalculated"] or 0)}
    hit = rows[rows["IDVP"] == 32]
    bid = hit.iloc[0]["GCText"] if len(hit) else None
    veic = base["D01"].set_index("IDV").loc[idv]
    ef_table = effective_emission_factors(base)
    res = calc.calculate_vehicle(
        base, gc, powertrain=veic["IDVPT"], battery_id=bid, idmpv=int(cen["IDMPV"]),
        idvmr=cen["IDVMR"], idefv=cen["IDEFV"], idapv=cen["IDAPV"],
        boundary=cen["Boundary"], ef_table=ef_table, supplied=supplied)
    return base, res, ef_table, cen


def test_compute_gera_as_quatro_tabelas(caso):
    base, res, ef_table, cen = caso
    ef = b1.ef_for(ef_table, cen["IDEFV"])
    out = b1.compute(res, base, ef, b1.Options(), boundary=cen["Boundary"])
    assert set(out) >= {"C15", "C16", "C34", "C35"}
    assert len(out["C16"]) == 1 and len(out["C34"]) == 1
    t = out["totals"]
    assert t["TOTAL"] == pytest.approx(
        t["INITIAL_PRODUCTION"] + t["LIFETIME_REPLACEMENTS"] + t["END_OF_LIFE"])
    assert t["INITIAL_PRODUCTION"] == pytest.approx(
        res["totals"]["GHGCradleToGate"], rel=1e-9)


def test_sem_massa_declarada_nao_calibra(caso):
    base, res, ef_table, cen = caso
    ef = b1.ef_for(ef_table, cen["IDEFV"])
    out = b1.compute(res, base, ef, b1.Options(), boundary=cen["Boundary"])
    m = out["C34"].iloc[0]
    assert m["AdjustmentKg"] == 0 and pd.isna(m["DiffKg"])


def test_modo_nao_zera_reposicoes(caso):
    base, res, ef_table, cen = caso
    ef = b1.ef_for(ef_table, cen["IDEFV"])
    out = b1.compute(res, base, ef, b1.Options(maintenance_mode="Não"),
                     boundary=cen["Boundary"])
    assert out["totals"]["LIFETIME_REPLACEMENTS"] == 0 and out["C15"].empty


def test_gravacao_e_idempotente(caso):
    base, res, ef_table, cen = caso
    ef = b1.ef_for(ef_table, cen["IDEFV"])
    out = b1.compute(res, base, ef, b1.Options(), boundary=cen["Boundary"])
    conn = sqlite3.connect(":memory:")
    from core import schema
    schema.create_schema(conn)
    conn.execute("PRAGMA foreign_keys=OFF")  # sem D07/D09: so a gravacao importa aqui
    for _ in range(2):
        b1.write_db(conn, "R1", ida=1, idcase=1, idv=int(cen["IDV"]), idea=int(cen["IDEA"]),
                    frames=out)
    n = conn.execute("SELECT COUNT(*) FROM C35_VehicleLifeStage").fetchone()[0]
    assert n == len(out["C35"])
    assert conn.execute("SELECT COUNT(*) FROM C16_EndOfLife").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM C15_Replacement").fetchone()[0] == len(out["C15"])


def test_relatorio_inclui_r12_a_r15(caso):
    from core import report
    base, res, ef_table, cen = caso
    ef = b1.ef_for(ef_table, cen["IDEFV"])
    out = b1.compute(res, base, ef, b1.Options(), boundary=cen["Boundary"])
    chave = (int(cen["IDV"]), int(cen["IDEA"]))
    R = report.build(base, {chave: res}, b1={chave: out})
    for rid in ("R12", "R13", "R14", "R15"):
        assert rid in R and len(R[rid]) > 0
        assert rid in report.TITLES
    assert "R12" not in report.build(base, {chave: res})


def test_rodada_grava_b1_e_estagios_fecham(tmp_path):
    """run.execute grava C15/C16/C34/C35; a soma dos estagios e o total do C35."""
    import shutil

    from core import analysis, project, run
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    project.create(conn, "B1")
    idefv = conn.execute("SELECT IDEFV FROM P10_EFVersion ORDER BY IDEFV LIMIT 1").fetchone()[0]
    apv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion LIMIT 1").fetchone()[0]
    cfg = dict(fuel="E27", norm="NBR", curve="Default", idefv=idefv, idmpv=1, idapv=apv)
    ida = analysis.create_ec(conn, "EC", "A0", cfg)
    rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
    run.execute(conn, path, rid)
    casos = conn.execute("SELECT COUNT(DISTINCT IDCase) FROM C35_VehicleLifeStage "
                         "WHERE RunID = ?", (rid,)).fetchone()[0]
    assert casos > 0
    assert conn.execute("SELECT COUNT(*) FROM C16_EndOfLife WHERE RunID = ?",
                        (rid,)).fetchone()[0] == casos
    assert conn.execute("SELECT COUNT(*) FROM C34_MassValidation WHERE RunID = ?",
                        (rid,)).fetchone()[0] == casos
    ini = conn.execute("SELECT MIN(GHGkg) FROM C35_VehicleLifeStage WHERE RunID = ? "
                       "AND Stage = 'INITIAL_PRODUCTION' AND SubStage = 'MATERIALS'",
                       (rid,)).fetchone()[0]
    assert ini > 0
    conn.close()


def _rodar(tmp_path, ajustar):
    import shutil

    from core import analysis, project, run
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    project.create(conn, "B1")
    idefv = conn.execute("SELECT IDEFV FROM P10_EFVersion ORDER BY IDEFV LIMIT 1").fetchone()[0]
    apv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion LIMIT 1").fetchone()[0]
    cfg = dict(fuel="E27", norm="NBR", curve="Default", idefv=idefv, idmpv=1, idapv=apv)
    ida = analysis.create_ec(conn, "EC", "A0", cfg)
    ajustar(conn, ida)
    rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
    run.execute(conn, path, rid)
    return conn, rid


def _soma(conn, rid, stage):
    return conn.execute("SELECT SUM(GHGkg) FROM C35_VehicleLifeStage WHERE RunID = ? "
                        "AND Stage = ?", (rid, stage)).fetchone()[0] or 0.0


def test_escolhas_do_usuario_mudam_o_resultado(tmp_path):
    from core import b1_choices
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "c").mkdir()
    conn, rid = _rodar(tmp_path / "a", lambda c, i: None)
    padrao = _soma(conn, rid, "LIFETIME_REPLACEMENTS")
    assert padrao > 0 and _soma(conn, rid, "END_OF_LIFE") > 0

    def sem_manut(c, i):
        b1_choices.save_maintenance(c, i, mode="Não", scenario="REFERENCE",
                                    vehicle_life_km=None, items=[])
        b1_choices.save_eol(c, i, "EXCLUDED")
    conn2, rid2 = _rodar(tmp_path / "b", sem_manut)
    assert _soma(conn2, rid2, "LIFETIME_REPLACEMENTS") == 0
    assert _soma(conn2, rid2, "END_OF_LIFE") == 0

    def pneu_dobrado(c, i):
        b1_choices.save_maintenance(c, i, mode="Sim", scenario="USER", vehicle_life_km=None,
                                    items=[{"IDMI": "TIRE", "IntervalKm": 20000.0,
                                            "Active": True}])
    conn3, rid3 = _rodar(tmp_path / "c", pneu_dobrado)
    assert _soma(conn3, rid3, "LIFETIME_REPLACEMENTS") > padrao


def test_escolha_invalida_e_recusada():
    from core import b1_choices
    conn = sqlite3.connect(":memory:")
    with pytest.raises(ValueError):
        b1_choices.save_eol(conn, 1, "QUALQUER")
    with pytest.raises(ValueError):
        b1_choices.save_maintenance(conn, 1, mode="Sim", scenario="USER", vehicle_life_km=None,
                                    items=[{"IDMI": "TIRE", "IntervalKm": 0}])


def test_massa_declarada_calibra_carroceria_e_chassi(tmp_path):
    """T38 ponta a ponta: o ajuste vai para A e B, a massa final fecha com a declarada."""
    (tmp_path / "m").mkdir()
    (tmp_path / "z").mkdir()
    conn0, rid0 = _rodar(tmp_path / "z", lambda c, i: None)
    est = conn0.execute("SELECT CalculatedMassKg FROM C34_MassValidation WHERE RunID = ?",
                        (rid0,)).fetchone()[0]

    def declarar(c, i):
        c.execute("UPDATE D07_AnalysisVehicle SET DeclaredMassKg = ?, MassAdjustmentKg = ?, "
                  "DeclaredSource = 'manual' WHERE IDA = ? AND IDCase = 1",
                  (est + 50.0, 50.0, i))
    conn, rid = _rodar(tmp_path / "m", declarar)
    row = conn.execute("SELECT DeclaredMassKg, CalculatedMassKg, AdjustmentKg, ResidualKg, "
                       "BodyShare, BodyChassisMassAfter, BodyChassisMassBefore "
                       "FROM C34_MassValidation WHERE RunID = ? AND IDCase = 1",
                       (rid,)).fetchone()
    assert row[0] == pytest.approx(est + 50.0) and row[2] == pytest.approx(50.0)
    assert row[3] == pytest.approx(0.0, abs=1e-6)
    assert 0 <= row[4] <= 1
    assert row[5] - row[6] == pytest.approx(50.0)
