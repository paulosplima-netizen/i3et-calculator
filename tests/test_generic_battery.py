"""Bateria de tracao parametrica (P58) e a rodada gravada (Fase A, passo 5)."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import analysis, battery, project, run

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
CFG = dict(fuel="E27", norm="NBR", curve="Default", idefv="BR23", idmpv=1,
           idapv="i3ET-BR23", power_rule="ExcelParity")


def test_p58_links_each_model_to_control_params(base):
    p58 = base["P58"]
    assert set(p58["IDBMd"]) == {"PB-HEV-indefinido", "PB-PHEV-indefinido", "PB-BEV-indefinido"}
    cp = set(base["P30"]["IDCP"])
    assert set(p58["IDCPMass"]) | set(p58["IDCPCarbon"]) <= cp


def test_generic_model_reads_effective_values(base):
    vals = {"X72": 0.5, "X88": 7.0, "X67": 6.0, "X83": 9.0, "X70": 5.0, "X86": 10.0}
    hev = battery.generic_model(base["P58"], "PB-HEV-indefinido", vals)
    assert hev["basis"] == "Power" and hev["mass_per_unit"] == 0.5
    assert hev["carbon_intensity"] == 7.0
    assert battery.generic_model(base["P58"], "G22-BEV200-LFP", vals) is None
    assert battery.generic_model(base["P58"], None, vals) is None
    with pytest.raises(KeyError):
        battery.generic_model(base["P58"], "PB-BEV-indefinido", {})


def test_generic_battery_changes_with_the_user_value(base):
    from core import calc
    gc = {i: 0.0 for i in range(1, 43)}
    gc.update({2: 0.0, 3: 83.6, 5: 68.4})
    common = dict(powertrain="BEV", battery_id="PB-BEV-indefinido", idmpv=1,
                  idvmr="BEV-G24", idefv="BR23", idapv="i3ET-BR23", supplied={3, 5})
    a = calc.calculate_vehicle(base, gc, generic_battery=dict(
        id="x", basis="Energy", mass_per_unit=5.8, carbon_intensity=9.6), **common)
    b = calc.calculate_vehicle(base, gc, generic_battery=dict(
        id="x", basis="Energy", mass_per_unit=6.8, carbon_intensity=9.6), **common)
    assert a["gc"][35] == pytest.approx(5.8 * 68.4)
    assert b["gc"][35] == pytest.approx(6.8 * 68.4)
    assert b["totals"]["GHGCradleToGate"] > a["totals"]["GHGCradleToGate"]


@pytest.fixture(scope="module")
def recorded_run(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("p") / "p.sqlite")
    shutil.copy(DB, path)
    conn = sqlite3.connect(path)
    project.create(conn, "Teste")
    ida = analysis.create_ec(conn, "EC", "A0", CFG)
    rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
    run.execute(conn, path, rid)
    ref = {(k, i): v for k, i, v in conn.execute(
        "SELECT CaseKey, IDInd, Value FROM P52_ExcelReferenceValue WHERE RefSet = 'CP_OUT_EC'")}
    out = {(k, i): v for k, i, v in conn.execute(
        "SELECT CaseKey, IDInd, Value FROM R45_PowertrainSummary WHERE RunID = ? "
        "AND ValueOrigin = 'Calculated'", (rid,))}
    yield ref, out
    conn.close()


def test_sheet_battery_formula_reproduces_row_45(recorded_run):
    """A fórmula (parâmetro × potência ou energia) reproduz a linha 45 do M2: 17,89 ·
    36,47 · 133,07 · 124,65 · 397,80 kg."""
    ref, out = recorded_run
    expected = {"A02": 0.46511627906976744 * ref[("A02", "O11")],
                "A03": 0.46511627906976744 * ref[("A03", "O11")],
                "A04": 5.813953488372093 * ref[("A04", "O19")],
                "A05": 5.813953488372093 * ref[("A05", "O19")],
                "A06": 5.813953488372093 * ref[("A06", "O19")]}
    assert expected["A06"] == pytest.approx(397.795, abs=0.01)
    assert expected["A02"] == pytest.approx(17.893, abs=0.01)


def test_recorded_combined_power_matches_exactly(recorded_run):
    ref, out = recorded_run
    for k in ("A01", "A02", "A03", "A04", "A05", "A06"):
        assert out[(k, "O12")] == pytest.approx(ref[(k, "O12")], rel=1e-9)


@pytest.mark.parametrize("case,tol", [("A01", 0.002), ("A02", 0.002), ("A03", 0.002),
                                      ("A04", 0.002), ("A05", 0.002), ("A06", 0.001)])
def test_recorded_ghg_is_close_to_the_sheet(recorded_run, case, tol):
    """Resíduo de até 0,2%: motor de partida e ar-condicionado do ICEV (docs/08, passo 5)."""
    ref, out = recorded_run
    assert out[(case, "O29")] == pytest.approx(ref[(case, "O29")], rel=tol)


@pytest.mark.parametrize("case,tol", [("A01", 0.003), ("A02", 0.003), ("A03", 0.003),
                                      ("A04", 0.003), ("A05", 0.003), ("A06", 0.001)])
def test_recorded_mass_is_close_to_the_sheet(recorded_run, case, tol):
    ref, out = recorded_run
    assert out[(case, "O20")] == pytest.approx(ref[(case, "O20")], rel=tol)
