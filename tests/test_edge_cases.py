"""What the calculator does when the data is incomplete, extreme or unusual.

Most of these describe a promise the project made in Documento 1: missing data
is reported rather than counted as zero, the user's own factors take
precedence, and a supplied value outranks the equation that would have
produced it. A promise with no test is a preference.
"""

from __future__ import annotations


import pandas as pd
import pytest

from core import battery, calc, loader, materials
from core import params as P
from core.log import Log

EMPTY_P19 = pd.DataFrame(columns=["IDBMd", "EnergyDensity", "PowerDensity",
                                  "RefEnergy", "GravimetricGHGDensity",
                                  "GHGMethod"])


def _project_vehicle(base, idv=1):
    d01 = base["D01"].set_index("IDV")
    cen = base["D02"][base["D02"]["IDV"] == idv].iloc[0]
    rows = base["D03"][base["D03"]["IDV"] == idv]
    gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
    hit = rows[rows["IDVP"] == 32]
    bid = hit.iloc[0]["GCText"] if len(hit) else None
    return dict(gc_input=gc, powertrain=d01.loc[idv]["IDVPT"], battery_id=bid,
                idmpv=int(cen["IDMPV"]), idvmr=cen["IDVMR"], idefv=cen["IDEFV"],
                idapv=cen["IDAPV"], boundary=cen["Boundary"])


# --- missing data ---------------------------------------------------------

def test_a_null_factor_is_not_zero_emissions(base):
    """It contributes nothing to the total and everything to the coverage."""
    args = _project_vehicle(base)
    r = calc.calculate_vehicle(base, **args)
    assert r["totals"]["MassNoFactor"] >= 0
    c11 = r["C11"]
    uncovered = c11[c11["GHGIDM"] == 0]
    assert (uncovered["MassIDM"] >= 0).all()
    # the share is a share: between zero and one, and consistent with the mass
    share = r["totals"]["ShareNoFactor"]
    assert 0.0 <= share <= 1.0
    assert share == pytest.approx(
        r["totals"]["MassNoFactor"] / r["totals"]["MassIDV"], rel=1e-9)


def test_a_material_with_no_factor_keeps_its_mass(base):
    row = pd.Series({"IDM": "999", "EFBasis": "mass", "EFBasisParam": None,
                     "ShareRole": "material"})
    ghg, has_factor = materials.emissions_for(row, 10.0, {}, None)
    assert ghg == 0.0 and has_factor is False


def test_an_unknown_battery_model_keeps_its_mass_and_says_so(base):
    log = Log()
    gc = {35: 300.0}
    out = battery.by_material(base["P19"], base["P20"], base["P09"],
                              pd.DataFrame(columns=["IDM", "IDEFV", "EF"]),
                              gc, battery_id="NAO-EXISTE", idefv="G22", log=log)
    assert len(out) == 1
    assert float(out["MassIDMpGGB"].sum()) == pytest.approx(300.0)
    assert int(out.iloc[0]["HasFactor"]) == 0
    assert any("NAO-EXISTE" in e.message for e in log.of("AVISO"))


def test_no_battery_means_no_battery_rows(base):
    for bid in (None, "", "-", "NA"):
        out = battery.by_material(base["P19"], base["P20"], base["P09"],
                                  pd.DataFrame(columns=["IDM", "IDEFV", "EF"]),
                                  {35: 300.0}, battery_id=bid, idefv="G22")
        assert out.empty, repr(bid)


# --- parameters -----------------------------------------------------------

def test_a_supplied_value_outranks_the_equation(base):
    """Documento 1, secao 10.4: what the user states, the model does not undo."""
    gc = {2: 120.0, 3: 60.0, 15: 999.0}
    free = P.resolve(dict(gc), powertrain="HEV", battery_id=None, p19=EMPTY_P19)
    kept = P.resolve(dict(gc), powertrain="HEV", battery_id=None, p19=EMPTY_P19,
                     supplied={15})
    assert free[15] == pytest.approx(120.0)
    assert kept[15] == pytest.approx(999.0)


def test_zero_inputs_do_not_raise(base):
    gc = {i: 0.0 for i in range(1, 43)}
    g = P.resolve(gc, powertrain="ICEV", battery_id=None, p19=EMPTY_P19)
    assert all(v == 0 or isinstance(v, float) for v in g.values())


def test_a_vehicle_of_zero_size_weighs_nothing_but_still_computes(base):
    args = _project_vehicle(base)
    args["gc_input"] = {i: 0.0 for i in args["gc_input"]}
    args["battery_id"] = None
    r = calc.calculate_vehicle(base, **args)
    assert r["totals"]["MassIDV"] >= 0
    assert r["totals"]["GHGperKg"] is None or r["totals"]["GHGperKg"] >= 0


# --- boundary -------------------------------------------------------------

def test_the_boundary_decides_whether_assembly_is_counted(base):
    args = _project_vehicle(base)
    with_asm = calc.calculate_vehicle(base, **{**args, "boundary": "MAT_ASM"})
    without = calc.calculate_vehicle(base, **{**args, "boundary": "MAT"})
    asm = with_asm["totals"]["GHGAssembly"]
    assert asm > 0
    assert with_asm["totals"]["GHGCradleToGate"] - without["totals"]["GHGCradleToGate"] \
        == pytest.approx(asm, rel=1e-12)
    # the assembly is reported in both cases -- what changes is the total
    assert without["totals"]["GHGAssembly"] == pytest.approx(asm)


# --- the user's own emission factors --------------------------------------

def _with_user_factors(base, d04_rows, d05_rows):
    clone = loader.Base(tables=dict(base.tables), param_hash=base.param_hash)
    clone.tables["D04"] = pd.DataFrame(d04_rows)
    clone.tables["D05"] = pd.DataFrame(d05_rows)
    return clone


def test_a_user_factor_overrides_the_published_one(base):
    ef = loader.effective_emission_factors(_with_user_factors(
        base,
        [{"IDEFV": "MEU", "DsEFV": "meu", "DateIDEFV": "2026-09-20",
          "GWPSet": "AR6", "SourceEFV": "eu", "LicenseEFV": "-",
          "BasedOnIDEFV": "G22"}],
        [{"IDM": "1", "IDEFV": "MEU", "EF": 42.0, "EFnotes": "valor proprio"}]))
    meu = ef[ef["IDEFV"] == "MEU"].set_index("IDM")
    assert meu.loc["1", "EF"] == pytest.approx(42.0)
    assert int(meu.loc["1", "IsUserDefined"]) == 1


def test_a_user_version_inherits_what_it_does_not_redefine(base):
    ef = loader.effective_emission_factors(_with_user_factors(
        base,
        [{"IDEFV": "MEU", "DsEFV": "meu", "DateIDEFV": "2026-09-20",
          "GWPSet": "AR6", "SourceEFV": "eu", "LicenseEFV": "-",
          "BasedOnIDEFV": "G22"}],
        [{"IDM": "1", "IDEFV": "MEU", "EF": 42.0, "EFnotes": "valor proprio"}]))
    g22 = ef[ef["IDEFV"] == "G22"].set_index("IDM")
    meu = ef[ef["IDEFV"] == "MEU"].set_index("IDM")
    assert len(meu) == len(g22), "a versao do usuario perdeu materiais herdados"
    for idm in g22.index:
        if idm == "1":
            continue                      # esse o usuario redefiniu
        seu, dele = meu.loc[idm, "EF"], g22.loc[idm, "EF"]
        if pd.isna(dele):
            assert pd.isna(seu), idm      # ausencia tambem se herda
        else:
            assert seu == pytest.approx(dele), idm


def test_changing_a_factor_changes_only_that_material(base):
    args = _project_vehicle(base)
    baseline = calc.calculate_vehicle(base, **args)
    ef = loader.effective_emission_factors(base)
    bumped = ef.copy()
    hit = (bumped["IDEFV"] == args["idefv"]) & (bumped["IDM"] == "1")
    bumped.loc[hit, "EF"] = bumped.loc[hit, "EF"] * 2
    doubled = calc.calculate_vehicle(base, **{**args, "ef_table": bumped})
    a = baseline["C11"].set_index("IDM")["GHGIDM"]
    b = doubled["C11"].set_index("IDM")["GHGIDM"]
    for idm in a.index:
        if idm == "1":
            continue
        assert b[idm] == pytest.approx(a[idm], rel=1e-12), idm
    assert b["1"] > a["1"]


# --- the project as a whole ------------------------------------------------

def test_every_project_vehicle_runs_without_errors(base):
    log = Log()
    results = calc.calculate(base, log=log)
    assert len(results) == len(base["D02"])
    erros = [f"{e.rule}: {e.message}" for e in log.of("ERRO")]
    assert not erros, "erros no calculo do projeto:\n  " + "\n  ".join(erros)


def test_a_heavier_vehicle_of_the_same_kind_emits_more(base):
    """BP01, BP02 and BP03 are the same powertrain in growing sizes."""
    r = calc.calculate(base)
    trio = [(r[(i, 1)]["totals"]["MassIDV"], r[(i, 1)]["totals"]["GHGCradleToGate"])
            for i in (1, 2, 3)]
    assert [m for m, _ in trio] == sorted(m for m, _ in trio)
    assert [g for _, g in trio] == sorted(g for _, g in trio)
