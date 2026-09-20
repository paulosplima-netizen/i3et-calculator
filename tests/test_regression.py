"""The twelve project vehicles, frozen.

These values are not an independent opinion about the right answer: they are
what this version of the core produces. A change that moves them is not
forbidden -- it has to be intentional, and it has to update
`tests/fixtures/regressao_bp.json` in the same commit, with the reason in the
message.

Regenerate with `python tools/freeze_regression.py`.
"""

from __future__ import annotations

import hashlib

import pytest

from core import calc

REL_TOL = 1e-9


def _results(base):
    return calc.calculate(base)


@pytest.fixture(scope="module")
def current(base):
    return _results(base)


def test_the_frozen_base_is_the_shipped_base(frozen):
    """If the database changed, the frozen numbers describe another base."""
    from tests.conftest import DB
    with open(DB, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    assert digest == frozen["base_sha256"], (
        "a base mudou desde o congelamento; rode tools/freeze_regression.py "
        "e explique no commit o que mudou")


def test_every_frozen_vehicle_is_still_calculated(current, frozen):
    assert {f"{i}/{e}" for i, e in current} == set(frozen["vehicles"])


@pytest.mark.parametrize("field", ["MassIDV", "GHGMaterials", "GHGAssembly",
                                   "GHGCradleToGate", "GHGperKg",
                                   "MassNoFactor", "ShareNoFactor"])
def test_totals_have_not_drifted(current, frozen, field):
    for key, expected in frozen["vehicles"].items():
        idv, idea = (int(x) for x in key.split("/"))
        got = current[(idv, idea)]["totals"][field]
        want = expected["totals"][field]
        if want is None:
            assert got is None, f"{expected['DsV']} {field}"
            continue
        assert got == pytest.approx(want, rel=REL_TOL), (
            f"{expected['DsV']} ({expected['IDVPT']}) {field}: "
            f"agora={got!r} congelado={want!r}")


def test_group_breakdown_has_not_drifted(current, frozen):
    for key, expected in frozen["vehicles"].items():
        idv, idea = (int(x) for x in key.split("/"))
        c10 = current[(idv, idea)]["C10"]
        got = {str(r.IDGG): (r.MassIDGG, r.GHGIDGG) for r in c10.itertuples()}
        assert set(got) == set(expected["by_group"]), expected["DsV"]
        for g, (mass, ghg) in expected["by_group"].items():
            assert got[g][0] == pytest.approx(mass, rel=REL_TOL), f"{expected['DsV']} {g} massa"
            assert got[g][1] == pytest.approx(ghg, rel=REL_TOL), f"{expected['DsV']} {g} GHG"


def test_totals_are_internally_consistent(current):
    """I12 and I13 — the parts add up to the whole, on every vehicle."""
    for (idv, idea), r in current.items():
        t = r["totals"]
        assert t["MassIDV"] == pytest.approx(float(r["C10"]["MassIDGG"].sum()), rel=1e-12)
        assert t["MassIDV"] == pytest.approx(float(r["C11"]["MassIDM"].sum()), rel=1e-9)
        assert t["GHGMaterials"] == pytest.approx(float(r["C11"]["GHGIDM"].sum()), rel=1e-9)
        expected = t["GHGMaterials"] + (t["GHGAssembly"] if t["Boundary"] == "MAT_ASM" else 0.0)
        assert t["GHGCradleToGate"] == pytest.approx(expected, rel=1e-12)


def test_electrified_vehicles_carry_battery_emissions(current, base):
    d01 = base["D01"].set_index("IDV")
    for (idv, idea), r in current.items():
        if d01.loc[idv]["IDVPT"] in ("BEV", "PHEV", "HEV"):
            assert len(r["C07"]), f"{d01.loc[idv]['DsV']} sem bateria"
            assert float(r["C07"]["MassIDMpGGB"].sum()) > 0


def test_the_calculation_run_is_reproducible(base, current):
    """Same base in, same numbers out — no hidden state between runs."""
    again = _results(base)
    for key, r in current.items():
        assert again[key]["totals"] == pytest.approx(r["totals"])
