"""The calculation, end to end.

Tables in, tables out. This module knows nothing about files or interfaces: it
is what the web app, the notebook and the tests all call.
"""

from __future__ import annotations

import pandas as pd

from . import assembly, battery, mass, materials, params, totals
from .log import Log


def calculate_vehicle(base, gc_input: dict[int, float], *, powertrain: str,
                      battery_id, idmpv: int, idvmr: str, idefv: str,
                      idapv: str, boundary: str = "MAT_ASM",
                      ef_table: pd.DataFrame | None = None,
                      supplied: set[int] | None = None,
                      log: Log | None = None) -> dict:
    """Run one vehicle through the whole chain.

    `gc_input` holds the exogenous parameters; the endogenous ones are computed
    here and overwrite whatever was supplied.
    """
    from .loader import effective_emission_factors

    log = log if log is not None else Log()
    ef_table = effective_emission_factors(base) if ef_table is None else ef_table

    gc = params.resolve(gc_input, powertrain=powertrain, battery_id=battery_id,
                        p19=base["P19"], supplied=supplied, log=log)

    c01 = mass.by_subgroup(base["P06"], base["P08"], gc,
                           idmpv=idmpv, powertrain=powertrain, log=log)
    c02 = mass.by_group(c01, gc, base["P04"])
    c03 = materials.by_material_group(c02, base["P16"], base["P09"], ef_table, gc,
                                      idvmr=idvmr, idefv=idefv, log=log)
    c07 = battery.by_material(base["P19"], base["P20"], base["P09"], ef_table, gc,
                              battery_id=battery_id, idefv=idefv, log=log)
    c13 = assembly.ghg(base["P21"], base["P22"], base["P23"], base["P25"], ef_table,
                       idapv=idapv, idefv=idefv, log=log)

    c10 = totals.by_group(c02, c03, c07)
    c11 = totals.by_material(c03, c07)
    c14 = totals.by_vehicle(c10, c13, boundary=boundary, c03=c03, c07=c07)

    return {"gc": gc, "C01": c01, "C02": c02, "C03": c03, "C07": c07,
            "C10": c10, "C11": c11, "C13": c13, "totals": c14, "log": log}


def calculate(base, *, log: Log | None = None) -> dict:
    """Run every (IDV, IDEA) of the project."""
    from .loader import effective_emission_factors

    log = log if log is not None else Log()
    ef_table = effective_emission_factors(base)
    d01 = base["D01"].set_index("IDV")
    d03 = base["D03"]

    results = {}
    for _, cen in base["D02"].iterrows():
        idv = int(cen["IDV"])
        vehicle = d01.loc[idv]
        rows = d03[d03["IDV"] == idv]
        gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
        battery_id = None
        hit = rows[rows["IDVP"] == 32]
        if len(hit):
            battery_id = hit.iloc[0]["GCText"]
        results[(idv, int(cen["IDEA"]))] = calculate_vehicle(
            base, gc, powertrain=vehicle["IDVPT"], battery_id=battery_id,
            idmpv=int(cen["IDMPV"]), idvmr=cen["IDVMR"], idefv=cen["IDEFV"],
            idapv=cen["IDAPV"], boundary=cen["Boundary"],
            ef_table=ef_table, log=log)
    return results
