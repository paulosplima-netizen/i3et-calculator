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

import pytest

from core import calc
from core import params as P

TOL = 1e-6
CAR_GROUPS = ["A", "B", "C", "D", "E", "F", "G", "H", "J"]

#: The residue of zeroing the negative balancing plug of the `Others` line in
#: the i3ET's own recipes (order 1e-04 of one group's mass). It only shows up
#: in the hybrids, whose group C carries it.
CAR_MAX_REL = 1e-4


def _idvmr_of(cfg, conhecidas):
    """The recipe the i3ET used for this configuration, as an IDVMR.

    The fixture records the column name (`ICEV-PBP_BISD2`); the base names the
    same recipe `PBP_BISD2`. Configurations whose recipe the base does not hold
    -- the `G`, `S` and `P` families each carry their own -- are left out of
    the comparison instead of being matched to the nearest guess.
    """
    nome = str(cfg.get("recipe") or "")
    if "-" not in nome:
        return None
    idvmr = nome.split("-", 1)[1].strip()
    return idvmr if idvmr in conhecidas else None


def _usable(base, i3et):
    conhecidas = set(base["P15"]["IDVMR"])
    for code in i3et["usable_configs"]:
        cfg = i3et["configs"][code]
        idvmr = _idvmr_of(cfg, conhecidas)
        if idvmr is None:
            continue
        yield code, cfg, idvmr


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

    A model the base does not describe never reaches this point: those
    configurations use recipes the base does not hold either. The behaviour for
    an undescribed model -- keep the mass, declare the factor absent, warn --
    is asserted in `test_edge_cases.py`.
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


def test_auxiliary_battery_reproduces_the_i3et(runs):
    """Emissions per kg, which is what the recipe determines.

    This used to differ by a constant 9.87% on the `BP` configurations: they
    charge the auxiliary battery's plastic to Average Plastic while the `G`
    ones charge it to Polypropylene. It was not two conventions in the
    spreadsheet -- it was two different recipes, and the base now holds both.
    """
    for code, (cfg, _r, c10) in runs.items():
        mass = float(c10["MassIDGG"].get("Iaux", 0.0))
        if mass <= 0:
            continue
        ours = float(c10["GHGIDGG"].get("Iaux", 0.0)) / mass
        theirs = cfg["expected"]["ghg_aux_battery_kgCO2e"] / mass
        assert ours == pytest.approx(theirs, rel=1e-9), code


def test_vehicle_materials_reproduce_the_i3et(runs):
    """The emissions of the vehicle's materials, group by group.

    This was the open item of 20/09/2026, and it is closed. The base now holds
    both recipe families the i3ET holds -- the consultancy's `BISD*` and the
    Berco ao Portao project's `PBP_BISD*` -- and each configuration uses the
    one the spreadsheet names on row 9 of its column. The ICEV and BEV
    configurations agree to machine precision; the hybrids carry the residue
    described in `CAR_MAX_REL`.
    """
    pior = None
    for code, (cfg, _r, c10) in runs.items():
        present = [g for g in CAR_GROUPS if g in c10.index]
        ours = float(c10.loc[present, "GHGIDGG"].sum())
        theirs = cfg["expected"]["ghg_materials_kgCO2e"]
        rel = abs(ours - theirs) / theirs
        if pior is None or rel > pior[1]:
            pior = (code, rel)
    assert pior[1] <= CAR_MAX_REL, (
        f"os materiais do veiculo divergem do i3ET: {pior[0]} esta a "
        f"{pior[1]:.2e} (limite {CAR_MAX_REL:.0e})")


def test_the_recipe_of_each_configuration_is_the_one_the_i3et_names(base, i3et):
    """The comparison must not guess which recipe to use.

    There is more than one recipe per powertrain, and `BP02` uses a variant its
    vehicle name does not reveal. The fixture records the name the spreadsheet
    gives, and the project's own scenarios have to match it.
    """
    d01 = base["D01"].set_index("IDV")
    d02 = base["D02"]
    conhecidas = set(base["P15"]["IDVMR"])
    for _, cen in d02.iterrows():
        code = d01.loc[int(cen["IDV"])]["DsV"]
        cfg = i3et["configs"].get(code)
        if cfg is None:
            continue
        esperado = _idvmr_of(cfg, conhecidas)
        assert esperado is not None, f"{code}: receita {cfg.get('recipe')} ausente da base"
        assert cen["IDVMR"] == esperado, (
            f"{code} usa {cen['IDVMR']} e o i3ET nomeia {cfg['recipe']}")
