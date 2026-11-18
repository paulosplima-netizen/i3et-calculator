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
