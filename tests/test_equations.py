"""Unit tests of the equations, with values worked out by hand.

These do not touch the database. If one of them fails, an equation changed --
which is either a bug or a decision that needs to be recorded in Documento 1.
"""

from __future__ import annotations

import pandas as pd
import pytest

from core import mass, params

EMPTY_P19 = pd.DataFrame(columns=["IDBMd", "EnergyDensity", "PowerDensity",
                                  "RefEnergy", "GravimetricGHGDensity", "GHGMethod"])


def test_plan_area_is_length_times_width():
    g = params.resolve({7: 5.0, 8: 1.9}, powertrain="ICEV", battery_id=None,
                       p19=EMPTY_P19)
    assert g[9] == pytest.approx(9.5)


def test_body_volume_is_plan_area_times_height():
    g = params.resolve({7: 5.0, 8: 1.9, 27: 1.6}, powertrain="ICEV",
                       battery_id=None, p19=EMPTY_P19)
    assert g[28] == pytest.approx(15.2)


def test_combined_power_is_the_larger_of_the_two_motors():
    g = params.resolve({2: 120.0, 3: 60.0}, powertrain="HEV", battery_id=None,
                       p19=EMPTY_P19)
    assert g[15] == pytest.approx(120.0)


def test_series_hybrids_run_on_the_electric_motor_alone():
    for pt in ("SHEV", "SPHEV"):
        g = params.resolve({2: 120.0, 3: 60.0}, powertrain=pt, battery_id=None,
                           p19=EMPTY_P19)
        assert g[15] == pytest.approx(60.0), pt


def test_robustness_multiplies_power_area_traction_and_complexity():
    g = params.resolve({2: 120.0, 3: 0.0, 7: 5.0, 8: 1.9, 14: 1.0},
                       powertrain="ICEV", battery_id=None, p19=EMPTY_P19)
    assert g[16] == pytest.approx(120.0 * 9.5 * 1.0 * 1.0)


def test_starter_is_four_percent_of_combustion_power():
    g = params.resolve({2: 120.0}, powertrain="ICEV", battery_id=None,
                       p19=EMPTY_P19)
    assert g[18] == pytest.approx(4.8)


def test_a_supplied_value_outranks_the_equation():
    g = params.resolve({2: 120.0, 18: 3.6}, powertrain="ICEV", battery_id=None,
                       p19=EMPTY_P19, supplied={18})
    assert g[18] == pytest.approx(3.6)


def test_hybrid_module_exists_only_in_parallel_hybrids():
    for pt, expected in (("HEV", 1.0), ("PHEV", 1.0), ("ICEV", 0.0),
                         ("BEV", 0.0), ("FCV", 0.0), ("SHEV", 0.0)):
        g = params.resolve({2: 100.0, 3: 50.0}, powertrain=pt, battery_id=None,
                           p19=EMPTY_P19)
        assert g[41] == expected, pt


def test_mass_follows_the_scaling_law():
    p06 = pd.DataFrame([{"IDMPV": 1, "IDSG": 1, "Beta": 0.5, "GCR": 4.0,
                         "MR": 100.0, "fLM": 1.0, "utGCR": "", "Reference": ""}])
    p08 = pd.DataFrame([{"IDSG": 1, "IDVP": 9, "IDG": 1, "IDGG": "A",
                         "ExcludedVPT": None}])
    c01 = mass.by_subgroup(p06, p08, {9: 16.0}, idmpv=1, powertrain="ICEV")
    assert c01.iloc[0]["ME"] == pytest.approx(200.0)      # 100 * (16/4)**0.5


def test_a_subgroup_excluded_by_powertrain_has_no_mass():
    p06 = pd.DataFrame([{"IDMPV": 1, "IDSG": 1, "Beta": 1.0, "GCR": 1.0,
                         "MR": 50.0, "fLM": 1.0, "utGCR": "", "Reference": ""}])
    p08 = pd.DataFrame([{"IDSG": 1, "IDVP": 2, "IDG": 1, "IDGG": "E",
                         "ExcludedVPT": "SHEV,SPHEV"}])
    assert mass.by_subgroup(p06, p08, {2: 10.0}, idmpv=1,
                            powertrain="SHEV").iloc[0]["ME"] == 0.0
    assert mass.by_subgroup(p06, p08, {2: 10.0}, idmpv=1,
                            powertrain="ICEV").iloc[0]["ME"] == pytest.approx(500.0)
