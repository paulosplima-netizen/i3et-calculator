"""The calculation, end to end.

Tables in, tables out. This module knows nothing about files or interfaces: it
is what the web app, the notebook and the tests all call.
"""

from __future__ import annotations

import pandas as pd

from . import (assembly, battery, ef_equivalence, mass, mass_calibration, materials,
               params, totals)
from .log import Log


def calculate_vehicle(base, gc_input: dict[int, float], *, powertrain: str,
                      battery_id, idmpv: int, idvmr: str, idefv: str,
                      idapv: str, boundary: str = "MAT_ASM",
                      ef_table: pd.DataFrame | None = None,
                      supplied: set[int] | None = None,
                      power_factors: tuple[float, float] | None = None,
                      generic_battery: dict | None = None,
                      mass_adjustment_kg: float = 0.0, body_share: float = 0.5,
                      log: Log | None = None) -> dict:
    """Run one vehicle through the whole chain.

    `gc_input` holds the exogenous parameters; the endogenous ones are computed
    here and overwrite whatever was supplied.

    `mass_adjustment_kg` e `body_share` (T38): ver core/mass_calibration.py.
    """
    from .loader import effective_emission_factors

    log = log if log is not None else Log()
    ef_table = effective_emission_factors(base) if ef_table is None else ef_table

    # Fatores de uma versao do GREET aplicados a receita de outra (P57, alerta I28).
    usados = set(base["P16"].loc[base["P16"]["IDVMR"] == idvmr, "IDM"].astype(str))
    if battery_id is not None:
        usados |= set(base["P20"].loc[base["P20"]["IDBMd"] == battery_id, "IDM"].astype(str))
    ef_table, ef_alerts = ef_equivalence.adapt(
        ef_table, idefv, usados, base.get("P57"), log=log, context=f"{idefv}/{idvmr}")

    gc = params.resolve(gc_input, powertrain=powertrain, battery_id=battery_id,
                        p19=base["P19"], supplied=supplied,
                        power_factors=power_factors, generic_battery=generic_battery,
                        constants=params.equation_constants(base.get("P59")), log=log)

    c01 = mass.by_subgroup(base["P06"], base["P08"], gc,
                           idmpv=idmpv, powertrain=powertrain, log=log)
    c02 = mass.by_group(c01, gc, base["P04"])
    # T38: a diferenca (declarada - calculada) vai para carroceria e chassi; com 0 nada muda.
    c02 = mass_calibration.apply_to_c02(c02, float(mass_adjustment_kg), float(body_share))
    c03 = materials.by_material_group(c02, base["P16"], base["P09"], ef_table, gc,
                                      idvmr=idvmr, idefv=idefv, log=log)
    c07 = battery.by_material(base["P19"], base["P20"], base["P09"], ef_table, gc,
                              battery_id=battery_id, idefv=idefv, generic=generic_battery,
                              log=log)
    c13 = assembly.ghg(base["P21"], base["P22"], base["P23"], base["P25"], ef_table,
                       idapv=idapv, idefv=idefv, log=log)

    c10 = totals.by_group(c02, c03, c07)
    c11 = totals.by_material(c03, c07)
    c14 = totals.by_vehicle(c10, c13, boundary=boundary, c03=c03, c07=c07)

    return {"gc": gc, "C01": c01, "C02": c02, "C03": c03, "C07": c07,
            "C10": c10, "C11": c11, "C13": c13, "totals": c14, "log": log,
            "ef_alerts": ef_alerts}


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
        # D03.IsCalculated = 0 num parametro endogeno significa que o valor foi
        # informado, e valor informado nao e desfeito pela equacao (Documento 1,
        # secao 10.4). E a mesma regra que a validacao contra o i3ET aplica.
        supplied = {int(r["IDVP"]) for _, r in rows.iterrows()
                    if not int(r["IsCalculated"] or 0)}
        battery_id = None
        hit = rows[rows["IDVP"] == 32]
        if len(hit):
            battery_id = hit.iloc[0]["GCText"]
        results[(idv, int(cen["IDEA"]))] = calculate_vehicle(
            base, gc, powertrain=vehicle["IDVPT"], battery_id=battery_id,
            idmpv=int(cen["IDMPV"]), idvmr=cen["IDVMR"], idefv=cen["IDEFV"],
            idapv=cen["IDAPV"], boundary=cen["Boundary"],
            ef_table=ef_table, supplied=supplied, log=log)
    return results
