"""The reference base must satisfy its own integrity rules.

Documento 2, capitulo 8. These run against the shipped database: if one fails,
the data was published in a state the specification forbids.
"""

from __future__ import annotations


from core import validate
from core.log import Log

CLOSURE_TOL = 1e-6


def _material_only(base, df, column, keys):
    """Sum of the mass fractions of each (recipe, group) pair.

    Only rows whose ShareRole is ``material`` are fractions of the mass; the
    ``process`` and ``breakdown`` rows carry other quantities and never enter a
    closure. Pairs whose sum is exactly zero are groups the recipe does not
    use — an absence, not a broken closure — so they are dropped here.
    """
    material = set(base["P09"].loc[base["P09"]["ShareRole"] == "material", "IDM"])
    only = df[df["IDM"].isin(material)]
    sums = only.groupby(keys)[column].sum()
    return sums[sums.abs() > CLOSURE_TOL]


def test_base_passes_every_structural_invariant(base):
    log = Log()
    ok = validate.check_base(base, log)
    erros = [f"{e.rule}: {e.message}" for e in log.of("ERRO")]
    assert ok, "invariantes violados:\n  " + "\n  ".join(erros)


def test_material_recipes_close_on_one(base):
    """I1 — only the rows that are actually mass fractions are summed."""
    sums = _material_only(base, base["P16"], "MshareGG", ["IDVMR", "IDGG"])
    bad = sums[(sums - 1).abs() > CLOSURE_TOL]
    assert bad.empty, f"receitas que nao fecham:\n{bad}"


def test_battery_recipes_close_on_one(base):
    """I2 — same, for the battery models that have a composition."""
    p20 = base["P20"]
    with_mass = p20[p20["BMshareGG"] > 0]["IDBMd"].unique()
    sums = _material_only(base, p20[p20["IDBMd"].isin(with_mass)],
                          "BMshareGG", ["IDBMd", "IDGG"])
    bad = sums[(sums - 1).abs() > CLOSURE_TOL]
    assert bad.empty, f"composicoes de bateria que nao fecham:\n{bad}"


def test_fuel_shares_close_on_one(base):
    """I3 — the energy carriers of each assembly process."""
    sums = base["P22"].groupby(["IDAPV", "IDAP"])["FuelShare"].sum()
    bad = sums[(sums - 1).abs() > CLOSURE_TOL]
    assert bad.empty, f"repartic. de combustiveis que nao fecha:\n{bad}"


def test_every_material_used_has_a_factor_row(base):
    """I4 — a row must exist even when its value is unknown."""
    used = set(base["P16"]["IDM"]) | set(base["P20"]["IDM"])
    versions = set(base["D02"]["IDEFV"])
    have = set(zip(base["P11"]["IDM"], base["P11"]["IDEFV"]))
    missing = {(m, v) for m in used for v in versions if (m, v) not in have}
    assert not missing, f"pares (IDM, IDEFV) ausentes de P11: {sorted(missing)[:10]}"


def test_every_subgroup_has_exactly_one_dimensioning_parameter(base):
    """I10 — otherwise a subgroup would be counted twice."""
    assert not base["P08"]["IDSG"].duplicated().any()


def test_mass_parameters_are_in_domain(base):
    """I6 — a negative exponent or a zero reference breaks the scaling law."""
    p06 = base["P06"]
    assert (p06["Beta"] >= 0).all()
    assert (p06["GCR"] > 0).all()
    assert (p06["MR"] >= 0).all()
    assert (p06["fLM"] > 0).all()


def test_no_reference_subgroup_has_zero_mass_by_accident(base):
    """A zero MR silently removes a subgroup from every vehicle.

    This is exactly what happened to the fuel tank (IDSG 26) and was only found
    by comparing against the i3ET. The test exists so it cannot happen twice.

    Two subgroups are zero on purpose — 38 (filters, gaskets, pads) and 39
    (tyres), whose mass is already inside the equipment that carries them and
    whose replacement is out of the cradle-to-gate scope. What tells the two
    cases apart is the Reference: a deliberate zero says why it is zero, an
    accidental one says nothing.
    """
    p06 = base["P06"]
    reference = p06["Reference"].fillna("").astype(str).str.strip()
    silent = p06[(p06["MR"] == 0) & (reference == "")]
    assert silent.empty, (
        "subgrupos com MR = 0 e sem justificativa: "
        f"{sorted(silent['IDSG'])}"
    )


def test_gravimetric_batteries_declare_their_carbon_intensity(base):
    p19 = base["P19"]
    grav = p19[p19["GHGMethod"] == "gravimetric"]
    assert grav["GravimetricGHGDensity"].notna().all()
    assert (grav["GravimetricGHGDensity"] > 0).all()


def test_emission_factors_are_never_negative(base):
    ef = base["P11"]["EF"].dropna()
    assert (ef >= 0).all()


def test_every_factor_declares_its_provenance(base):
    """The Argonne terms require saying that the data was processed."""
    notes = base["P11"]["EFnotes"]
    assert notes.notna().all() and (notes.str.len() > 0).all()
