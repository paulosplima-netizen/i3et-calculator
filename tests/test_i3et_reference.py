"""The core against the i3ET, as a test rather than as a report.

`tools/validate_core.py` prints the acceptance table for a person to read. This
module asserts the one line of it that must never change: no configuration
diverges from the spreadsheet without an explanation on record.

The classification lives in the tool and is imported here so that the report
and the test can never disagree about what counts as a divergence.
"""

from __future__ import annotations

import pytest

from core import calc
from core import params as P
from tools.validate_core import KNOWN, NOT_SCALED_BY, TOL, classify


def _run(base, cfg, ef_i3et):
    gc = {int(k): (v if isinstance(v, (int, float)) else 0.0)
          for k, v in cfg["gc"].items()}
    bid = cfg["gc"].get("32")
    bid = None if bid in (None, "-", "NA") else str(bid).strip()
    supplied = {i for i in P.ENDOGENOUS
                if isinstance(cfg["gc"].get(str(i)), (int, float))}
    idvmr = base["D02"].iloc[0]["IDVMR"]
    return calc.calculate_vehicle(
        base, gc, powertrain=cfg["powertrain"], battery_id=bid, idmpv=1,
        idvmr=idvmr, idefv="FIXTURE", idapv="A-EF", boundary="MAT",
        ef_table=ef_i3et, supplied=supplied)


@pytest.fixture(scope="module")
def classified(base, i3et, ef_i3et):
    p08 = {int(r.IDSG): int(r.IDVP) for r in base["P08"].itertuples()}
    out = {}
    for code in i3et["usable_configs"]:
        cfg = i3et["configs"][code]
        r = _run(base, cfg, ef_i3et)
        bucket, factor = classify(code, cfg, r, p08)
        out[code] = (bucket, factor, r["totals"]["MassIDV"],
                     cfg["expected"]["vehicle_mass_kg"])
    return out


def test_no_configuration_diverges_without_an_explanation(classified):
    """The acceptance criterion of Documento 1, secao 17.1."""
    bad = {c: v for c, v in classified.items() if v[0] == "sem explicacao"}
    assert not bad, "configuracoes divergentes e nao explicadas:\n  " + "\n  ".join(
        f"{c}: nossa={v[2]:.4f}  i3ET={v[3]:.4f}  dif={v[2]-v[3]:+.4f}"
        for c, v in sorted(bad.items()))


def test_every_known_divergence_is_documented(classified):
    """A bucket without a written explanation is an undocumented divergence."""
    used = {v[0] for v in classified.values()}
    undocumented = used - {"exata", "leveza", "sem explicacao"} - set(KNOWN)
    assert not undocumented, f"divergencias sem texto no KNOWN: {sorted(undocumented)}"


def test_the_lightweighting_bucket_is_a_single_constant_factor(classified):
    """M5 is out of scope, but it must look like M5: one factor per vehicle.

    If a configuration lands in this bucket with a factor that is not constant
    across its scaled subgroups, `classify` would not have put it there -- so
    what this checks is that the factors are plausible lightweighting values
    rather than an arbitrary spread hiding a real error.
    """
    factors = sorted({round(v[1], 6) for v in classified.values()
                      if v[0] == "leveza" and v[1]})
    assert all(0.5 <= f <= 1.5 for f in factors), f"fatores implausiveis: {factors}"


def test_exact_configurations_are_exact_to_machine_precision(classified):
    exatas = {c: v for c, v in classified.items() if v[0] == "exata"}
    assert exatas, "nenhuma configuracao reproduz o i3ET"
    for code, (_, _, ours, theirs) in exatas.items():
        assert abs(ours - theirs) <= TOL * max(1.0, abs(theirs)), code


def test_the_usable_configurations_were_not_silently_reduced(i3et, classified):
    """A shrinking fixture would make every other assertion easier to pass."""
    assert len(classified) == len(i3et["usable_configs"])
    assert len(classified) >= 70


def test_subgroups_outside_the_scaling_law_are_declared(base):
    """NOT_SCALED_BY names dimensioning parameters, not subgroups."""
    idvp = set(base["P07"]["IDVP"])
    assert NOT_SCALED_BY <= idvp
