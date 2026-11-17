"""Integrity and conservation invariants.

Documento 2, capitulo 8. I1 to I11 are checked when the base is loaded; I12 and
I13 after the calculation. A violated invariant blocks export: the calculator
does not hand over a number it cannot reconcile with itself.
"""

from __future__ import annotations


from .log import Log

CLOSURE_TOL = 1e-6
CONSERVATION_TOL = 1e-9


def _closure(df, keys, column, rule, log, p09):
    material = p09.loc[p09["ShareRole"] == "material", "IDM"]
    only = df[df["IDM"].isin(material)]
    sums = only.groupby(keys, as_index=False)[column].sum()
    # A group whose fractions sum to exactly zero is a group the recipe does
    # not use (e.g. a battery chemistry that carries no plastics). That is an
    # absence, not a closure violation: only non-empty groups must close on 1.
    present = sums[sums[column].abs() > CLOSURE_TOL]
    bad = present[(present[column] - 1).abs() > CLOSURE_TOL]
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


def check_result(result: dict, log: Log, context: str | None = None) -> bool:
    """I12 and I13 — mass and emissions must close.

    `context` names the vehicle and scenario, so a failing line in the exported
    log says which result it belongs to rather than only which rule broke.
    """
    ok = True
    mass_total = float(result["totals"]["MassIDV"])
    by_material = float(result["C11"]["MassIDM"].sum())
    if not _close(by_material, mass_total):
        log.error("I12", f"massa por material {by_material:.9f} != "
                         f"massa do veiculo {mass_total:.9f}", context)
        ok = False
    ghg_total = float(result["totals"]["GHGIDV"])
    ghg_material = float(result["C11"]["GHGIDM"].sum())
    ghg_group = float(result["C10"]["GHGIDGG"].sum())
    if not _close(ghg_material, ghg_total) or not _close(ghg_group, ghg_total):
        log.error("I13", f"emissoes nao fecham: por material {ghg_material:.6f}, "
                         f"por grupo {ghg_group:.6f}, total {ghg_total:.6f}", context)
        ok = False
    return ok


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= CONSERVATION_TOL * max(1.0, abs(a), abs(b))


# --------------------------------------------------------------------------
# Regras I16 a I23 (Documento 7, §6): analise, casos, D12 e R45.
#   `check_analysis` devolve a lista de problemas de uma analise; vazia quando
#   esta consistente. `check_run_origin` cobre I23 sobre o R45 de uma rodada.
# --------------------------------------------------------------------------
def check_analysis(conn, ida: int) -> list[str]:
    q = lambda sql, *a: conn.execute(sql, a).fetchall()  # noqa: E731
    problems: list[str] = []
    head = q("SELECT Mode, IDVC, IDMVRef, IDEFV, IDMPV, IDAPV, Boundary FROM D06_Analysis "
             "WHERE IDA = ?", ida)
    if not head:
        return [f"analysis {ida} does not exist"]
    mode, idvc, ref, idefv, idmpv, idapv, boundary = head[0]
    cases = q("SELECT IDCase, CaseRole, IDVPT, IDV, IDEA FROM D07_AnalysisVehicle "
              "WHERE IDA = ? ORDER BY IDCase", ida)

    if mode == "EC":                                                      # I16
        pts = [c[2] for c in cases]
        if len(cases) != 6 or len(set(pts)) != 6 or cases[0][1] != "REF":
            problems.append("I16: an EC analysis needs six cases, one per powertrain, "
                            "the first being REF")
    elif mode == "FC":                                                    # I17
        if not 1 <= len(cases) <= 7 or any(c[1] != "FC" for c in cases):
            problems.append("I17: an FC analysis has 1 to 7 cases, all with CaseRole FC")

    n = q("SELECT COUNT(*) FROM (SELECT IDEFV FROM P10_EFVersion WHERE IDEFV = ? "          # I18
          "UNION ALL SELECT IDEFV FROM D04_UserEFVersion WHERE IDEFV = ?)", idefv, idefv)[0][0]
    if n != 1:
        problems.append(f"I18: IDEFV {idefv!r} resolves to {n} versions, expected 1")

    for idcase, _, _, idv, idea in cases:                                 # I19
        alt = q("SELECT IDEFV, IDMPV, IDAPV, Boundary FROM D02_EvaluationAlternative "
                "WHERE IDV = ? AND IDEA = ?", idv, idea)
        if not alt or tuple(alt[0]) != (idefv, idmpv, idapv, boundary):
            problems.append(f"I19: case {idcase} has versions different from the analysis")

    bad = q("SELECT d.IDCP FROM D08_ControlParamValue d JOIN P30_ControlParam p USING (IDCP) "
            "WHERE d.IDA = ? AND p.IsCalculated = 1", ida)                # I20
    if bad:
        problems.append("I20: D08 has values for calculated parameters: "
                        + ", ".join(r[0] for r in bad))

    if mode == "EC" and ref is not None:                                  # I21
        cat = q("SELECT MarketGroup, IDMVSelecao FROM P29_VehicleCategory WHERE IDVC = ?", idvc)
        mv = q("SELECT IDVPT, MarketGroup FROM P26_MarketVehicle WHERE IDMV = ?", ref)
        ok = bool(cat) and (ref == cat[0][1] or (bool(mv) and mv[0][0] == "ICEV"
                                                 and mv[0][1] == cat[0][0]))
        if not ok:
            problems.append("I21: the reference vehicle is not an ICEV of the category "
                            "market group nor its SELEÇÃO")

    pt_of = {c[0]: c[2] for c in cases}                                   # I22
    for idcase, in q("SELECT IDCase FROM D12_CombinedPowerOverride WHERE IDA = ?", ida):
        if pt_of.get(idcase) not in ("HEV", "PHEV"):
            problems.append(f"I22: case {idcase} has a D12 row but is not HEV or PHEV")
    return problems


def check_run_origin(conn, run_id: str) -> list[str]:
    """I23: ValueOrigin = Calculated only where P51.CalcStatus = Calculated."""
    rows = conn.execute(
        "SELECT DISTINCT r.IDInd FROM R45_PowertrainSummary r JOIN P51_OutputIndicator p "
        "USING (IDInd) WHERE r.RunID = ? AND r.ValueOrigin = 'Calculated' "
        "AND p.CalcStatus <> 'Calculated'", (run_id,)).fetchall()
    return [f"I23: indicator {r[0]} is marked Calculated but is not calculated by the core"
            for r in rows]
