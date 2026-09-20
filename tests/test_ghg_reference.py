"""The emissions side of the comparison against the i3ET.

`test_i3et_reference.py` checks the mass (module M1). This module checks what
M2 does with that mass. The three parts behave differently and are asserted
separately, because lumping them together would hide which one moved:

  fluids            exact, for the reference family of configurations
  traction battery  exact, for every configuration
  auxiliary battery exact in intensity, with one known and measured divergence
  vehicle materials NOT yet reconciled -- see `test_car_materials_...` below

The reference family is G01..G29 and BP01..BP12: the configurations whose
material recipes the base actually holds. The i3ET lets every configuration
column carry its own composition; the relational model carries it per recipe
(IDVMR), which is the granularity of Documento 2.
"""

from __future__ import annotations

import re

import pytest

from core import calc
from core import params as P

TOL = 1e-6
#: Configurations whose recipes the base holds. GL/SL/PL are lightweighting
#: families (module M5) and P/S are alternative scenarios with compositions of
#: their own.
REFERENCE_FAMILY = re.compile(r"^(G\d{1,2}|BP\d{2})$")
CAR_GROUPS = ["A", "B", "C", "D", "E", "F", "G", "H", "J"]

#: The i3ET's BP columns charge the auxiliary battery's plastic to Average
#: Plastic (IDM 10, 4.4833 kg CO2e/kg) while its G columns charge it to
#: Polypropylene (2.6074). The base follows the G columns, which is also what
#: the simulator's own recipe says. The gap is a fixed 9.87% of a component
#: worth about 18 kg CO2e -- under 0.05% of the vehicle. Relatorio de
#: Divergencias, item 6.
AUX_BP_RATIO = 1.098665
#: How far the vehicle materials are from the i3ET today. Not an accepted
#: value: a ceiling, so that the gap cannot widen unnoticed while it is open.
CAR_MAX_REL = 0.10


def _usable(base, i3et):
    rec = {r["IDVPT"]: r["IDVMR"] for r in base["P15"].to_dict("records")}
    for code in i3et["usable_configs"]:
        cfg = i3et["configs"][code]
        if not REFERENCE_FAMILY.match(code):
            continue
        if cfg["powertrain"] not in rec:
            continue          # FCV has no recipe in the base -- known divergence
        yield code, cfg, rec[cfg["powertrain"]]


def _run(base, cfg, idvmr, ef_i3et):
    gc = {int(k): (v if isinstance(v, (int, float)) else 0.0)
          for k, v in cfg["gc"].items()}
    bid = cfg["gc"].get("32")
    bid = None if bid in (None, "-", "NA") else str(bid).strip()
    supplied = {i for i in P.ENDOGENOUS
                if isinstance(cfg["gc"].get(str(i)), (int, float))}
    return calc.calculate_vehicle(
        base, gc, powertrain=cfg["powertrain"], battery_id=bid, idmpv=1,
        idvmr=idvmr, idefv="FIXTURE", idapv="A-EF", boundary="MAT",
        ef_table=ef_i3et, supplied=supplied)


@pytest.fixture(scope="module")
def runs(base, i3et, ef_i3et):
    """Only the configurations whose mass already reproduces the i3ET.

    Comparing emissions where the masses differ would only re-measure the
    lightweighting factor of module M5, which `test_i3et_reference.py` already
    accounts for. What is asked here is narrower and stricter: where M1 agrees,
    M2 must agree too.
    """
    out = {}
    for code, cfg, idvmr in _usable(base, i3et):
        r = _run(base, cfg, idvmr, ef_i3et)
        theirs = cfg["expected"]["vehicle_mass_kg"]
        if abs(r["totals"]["MassIDV"] - theirs) > TOL * max(1.0, abs(theirs)):
            continue
        out[code] = (cfg, r, r["C10"].set_index("IDGG"))
    assert len(out) >= 12, "familia de referencia menor do que o esperado"
    return out


def test_fluids_reproduce_the_i3et(runs):
    """Group K. Until 20/09/2026 this group carried mass and no emissions."""
    for code, (cfg, _r, c10) in runs.items():
        ours = float(c10["GHGIDGG"].get("K", 0.0))
        theirs = cfg["expected"]["ghg_fluids_kgCO2e"]
        assert ours == pytest.approx(theirs, rel=1e-9), code


def test_fluids_are_never_silently_zero(runs):
    """A vehicle with fluid mass and no fluid emissions is the old bug."""
    for code, (_cfg, _r, c10) in runs.items():
        if float(c10["MassIDGG"].get("K", 0.0)) > 0:
            assert float(c10["GHGIDGG"].get("K", 0.0)) > 0, code


def _battery_is_described(base, cfg):
    bid = cfg["gc"].get("32")
    if bid in (None, "", "-", "NA"):
        return False
    return str(bid).strip() in set(base["P19"]["IDBMd"])


def test_traction_battery_reproduces_the_i3et(base, runs):
    """For every battery model the base actually describes.

    The G family cites models that live in the i3ET's battery sheet and not in
    P19. Those are covered by the next test, which is about honesty rather
    than about agreement.
    """
    checked = 0
    for code, (cfg, r, _c10) in runs.items():
        if not _battery_is_described(base, cfg):
            continue
        ours = float(r["C07"]["GHGIDMpGGB"].sum()) if len(r["C07"]) else 0.0
        theirs = cfg["expected"]["ghg_pe_battery_kgCO2e"] or 0.0
        assert ours == pytest.approx(theirs, rel=1e-9, abs=1e-9), code
        checked += 1
    assert checked >= 9, "nenhum modelo de bateria conferido"


def test_an_undescribed_battery_is_reported_and_not_zeroed(base, i3et, ef_i3et):
    """A battery the base does not describe must not cost zero in silence.

    It keeps its mass, its factor is declared absent, the coverage picks it up
    and the log says so. This is the rule of Documento 1, secao 13.3 applied to
    the one place where it is easiest to break.
    """
    for code, cfg, idvmr in _usable(base, i3et):
        bid = cfg["gc"].get("32")
        if bid in (None, "", "-", "NA") or _battery_is_described(base, cfg):
            continue
        r = _run(base, cfg, idvmr, ef_i3et)
        c07 = r["C07"]
        assert len(c07), f"{code}: bateria {bid} sumiu do resultado"
        assert float(c07["MassIDMpGGB"].sum()) > 0, code
        assert (c07["HasFactor"] == 0).all(), code
        assert r["totals"]["MassNoFactor"] > 0, code
        assert any(str(bid) in e.message for e in r["log"].of("AVISO")), code
        return
    pytest.skip("todas as configuracoes citam modelos descritos na base")


def test_auxiliary_battery_matches_the_g_family_intensity(runs):
    """Emissions per kg, which is what the recipe determines.

    The G columns of the i3ET and the base agree exactly. The BP columns differ
    by a constant factor because of the plastic they charge it to -- asserted
    here so that the difference stays that one, known cause.
    """
    for code, (cfg, _r, c10) in runs.items():
        mass = float(c10["MassIDGG"].get("Iaux", 0.0))
        if mass <= 0:
            continue
        ours = float(c10["GHGIDGG"].get("Iaux", 0.0)) / mass
        theirs = cfg["expected"]["ghg_aux_battery_kgCO2e"] / mass
        expected = theirs / (AUX_BP_RATIO if code.startswith("BP") else 1.0)
        assert ours == pytest.approx(expected, rel=1e-5), code


def test_car_materials_stay_within_the_documented_gap(runs):
    """OPEN ITEM -- Relatorio de Divergencias, item 7.

    The mass of the vehicle matches the i3ET exactly and its distribution among
    materials does not: the base's recipes (P16, from the simulator) put less
    steel and more plastic than the i3ET's own composition for the same
    recipe name. Until that is settled this test is a ratchet, not an
    acceptance: it fails if the distance grows.
    """
    worst = None
    for code, (cfg, _r, c10) in runs.items():
        present = [g for g in CAR_GROUPS if g in c10.index]
        ours = float(c10.loc[present, "GHGIDGG"].sum())
        theirs = cfg["expected"]["ghg_materials_kgCO2e"]
        rel = abs(ours - theirs) / theirs
        if worst is None or rel > worst[1]:
            worst = (code, rel)
    assert worst[1] <= CAR_MAX_REL, (
        f"a diferenca nos materiais do veiculo cresceu: {worst[0]} "
        f"esta a {worst[1]:.2%} (limite documentado {CAR_MAX_REL:.0%})")


