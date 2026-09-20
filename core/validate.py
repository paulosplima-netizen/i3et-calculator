"""Integrity and conservation invariants.

Documento 2, capitulo 8. I1 to I11 are checked when the base is loaded; I12 and
I13 after the calculation. A violated invariant blocks export: the calculator
does not hand over a number it cannot reconcile with itself.
"""

from __future__ import annotations

import pandas as pd

from .log import Log

CLOSURE_TOL = 1e-6
CONSERVATION_TOL = 1e-9


def _closure(df, keys, column, rule, log, p09):
    material = p09.loc[p09["ShareRole"] == "material", "IDM"]
    only = df[df["IDM"].isin(material)]
    sums = only.groupby(keys, as_index=False)[column].sum()
    bad = sums[(sums[column] - 1).abs() > CLOSURE_TOL]
    for _, r in bad.iterrows():
        log.error(rule, f"{' / '.join(str(r[k]) for k in keys)}: soma = {r[column]:.9f}")
    return len(bad) == 0


def check_base(base, log: Log) -> bool:
    """I1 to I11 and I14/I15 — structure and domains of the reference base."""
    ok = True
    p09 = base["P09"]
    ok &= _closure(base["P16"], ["IDVMR", "IDGG"], "MshareGG", "I1", log, p09)
    with_mass = base["P20"][base["P20"]["BMshareGG"] > 0]["IDBMd"].unique()
    ok &= _closure(base["P20"][base["P20"]["IDBMd"].isin(with_mass)],
                   ["IDBMd", "IDGG"], "BMshareGG", "I2", log, p09)

    shares = base["P22"].groupby(["IDAPV", "IDAP"], as_index=False)["FuelShare"].sum()
    bad = shares[(shares["FuelShare"] - 1).abs() > CLOSURE_TOL]
    for _, r in bad.iterrows():
        log.error("I3", f"{r['IDAPV']} / processo {r['IDAP']}: soma = {r['FuelShare']:.9f}")
        ok = False

    # I10 — one dimensioning parameter per subgroup
    dup = base["P08"]["IDSG"].duplicated().sum()
    if dup:
        log.error("I10", f"{dup} subgrupos com mais de um parametro dimensionador")
        ok = False

    # I11 — battery coherent with the powertrain
    d01 = base["D01"].set_index("IDV")
    d03 = base["D03"]
    for idv, v in d01.iterrows():
        hit = d03[(d03["IDV"] == idv) & (d03["IDVP"] == 32)]
        declared = hit.iloc[0]["GCText"] if len(hit) else None
        electrified = v["IDVPT"] in ("BEV", "PHEV", "HEV", "SHEV", "SPHEV", "FCEV")
        if electrified and declared in (None, "", "-", "NA"):
            log.error("I11", f"veiculo {idv} ({v['IDVPT']}) sem bateria de tracao")
            ok = False
        if v["IDVPT"] == "ICEV" and declared not in (None, "", "-", "NA"):
            log.warn("I11", f"veiculo {idv} e ICEV mas declara a bateria {declared}")

    # I9 — recipe consistent with the powertrain (a warning, never an error)
    p15 = base["P15"].set_index("IDVMR")
    for _, cen in base["D02"].iterrows():
        recipe = p15.loc[cen["IDVMR"]] if cen["IDVMR"] in p15.index else None
        if recipe is None:
            log.error("I9", f"receita {cen['IDVMR']} inexistente")
            ok = False
        elif recipe["IDVPT"] != d01.loc[int(cen["IDV"])]["IDVPT"]:
            log.warn("I9", f"veiculo {cen['IDV']} usa a receita {cen['IDVMR']} "
                           f"({recipe['IDVPT']}) sendo {d01.loc[int(cen['IDV'])]['IDVPT']}")

    # I14 — user versions must not collide with the base
    d04 = base.get("D04")
    if d04 is not None and len(d04):
        clash = set(d04["IDEFV"]) & set(base["P10"]["IDEFV"])
        if clash:
            log.error("I14", f"versoes do usuario colidindo com a base: {sorted(clash)}")
            ok = False
        if d04["SourceEFV"].isna().any() or (d04["SourceEFV"] == "").any():
            log.error("I15", "versao do usuario sem procedencia declarada")
            ok = False
    return ok


def check_result(result: dict, log: Log) -> bool:
    """I12 and I13 — mass and emissions must close."""
    ok = True
    mass_total = float(result["totals"]["MassIDV"])
    by_material = float(result["C11"]["MassIDM"].sum())
    if not _close(by_material, mass_total):
        log.error("I12", f"massa por material {by_material:.9f} != "
                         f"massa do veiculo {mass_total:.9f}")
        ok = False
    ghg_total = float(result["totals"]["GHGIDV"])
    ghg_material = float(result["C11"]["GHGIDM"].sum())
    ghg_group = float(result["C10"]["GHGIDGG"].sum())
    if not _close(ghg_material, ghg_total) or not _close(ghg_group, ghg_total):
        log.error("I13", f"emissoes nao fecham: por material {ghg_material:.6f}, "
                         f"por grupo {ghg_group:.6f}, total {ghg_total:.6f}")
        ok = False
    return ok


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= CONSERVATION_TOL * max(1.0, abs(a), abs(b))
