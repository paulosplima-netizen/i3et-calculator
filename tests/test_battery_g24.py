"""Modelos de bateria do GREET 2024 em P18, P19 e P20 (bloco B0, item 4)."""

from __future__ import annotations

import os

import pytest

from core import battery, loader
from core.loader import effective_emission_factors

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(REPO, "data", "base_referencia.sqlite")
REQUIRED = ("G24-HEV-Ni-MH", "G24-PHEV50-NMC111", "G24-BEV300-NMC111")


@pytest.fixture(scope="module")
def base():
    return loader.load_sqlite(BASE)


def _g24(base):
    p19 = base["P19"]
    return p19[p19["IDBMd"].str.startswith("G24-")]


def test_all_g24_models_are_in_the_base(base):
    p19 = _g24(base)
    assert len(p19) == 66
    assert set(REQUIRED) <= set(p19["IDBMd"])
    assert set(p19["IDEFV"]) == {"G24"}
    assert set(p19["IDVPT"]) <= {"HEV", "PHEV", "BEV", "FCEV"}
    assert set(p19["GHGMethod"]) == {"composition"}


def test_each_model_has_a_full_recipe_that_sums_to_one(base):
    p20 = base["P20"].merge(base["P09"][["IDM", "ShareRole"]], on="IDM")
    for bid in _g24(base)["IDBMd"]:
        rows = p20[(p20["IDBMd"] == bid) & (p20["ShareRole"] == "material")]
        assert rows["BMshareGG"].sum() == pytest.approx(1.0, abs=1e-3), bid


def test_reference_weight_follows_the_sizing_basis(base):
    """Energia x massa por kWh (PHEV, BEV) ou potencia x massa por kW (HEV, FCEV)."""
    for _, r in _g24(base).iterrows():
        if r["IDVPT"] in ("HEV", "FCEV"):
            assert r["PowerDensity"] > 0, r["IDBMd"]
            assert r["RefWeight"] == pytest.approx(r["RefPower"] * r["PowerDensity"], rel=1e-9)
        else:
            assert r["RefWeight"] == pytest.approx(r["RefEnergy"] * r["EnergyDensity"], rel=1e-6)


@pytest.mark.parametrize("bid", REQUIRED)
def test_composition_path_reproduces_the_reference_mass(base, bid):
    row = base["P19"][base["P19"]["IDBMd"] == bid].iloc[0]
    gc = {battery.IDVP_BATTERY_MASS: float(row["RefWeight"]), 5: float(row["RefEnergy"])}
    ef = effective_emission_factors(base)
    c07 = battery.by_material(base["P19"], base["P20"], base["P09"], ef, gc,
                              battery_id=bid, idefv="G24")
    assert (c07["CountsAsMass"] * c07["MassIDMpGGB"]).sum() == pytest.approx(
        row["RefWeight"], rel=1e-3)
    assert c07["GHGIDMpGGB"].sum() > 0
