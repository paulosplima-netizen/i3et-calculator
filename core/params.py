"""Endogenous vehicle parameters.

Documento 1, secao 7.2. These are the parameters the model derives from others
before any mass is estimated. They are never typed by the user: if a value is
present for one of them it is overwritten, and the log says so.
"""

from __future__ import annotations

import math

import pandas as pd

#: IDVP of every parameter this module computes, in dependency order.
ENDOGENOUS = [9, 15, 16, 18, 28, 33, 34, 36, 35, 37, 42]

_NOT_APPLICABLE = object()   # the spreadsheet's "ND"


def _battery(p19: pd.DataFrame, idbmd):
    if idbmd in (None, "", "-", "NA"):
        return None
    hit = p19[p19["IDBMd"] == idbmd]
    return None if hit.empty else hit.iloc[0]


#: Powertrains that carry a hybrid combination module. In the i3ET this is an
#: inline condition inside the mass formula; here it is a derived parameter, so
#: the rule is stated once instead of being repeated in every column.
HYBRID_COMBINATION = ("HEV", "PHEV")


def resolve(gc: dict[int, float], *, powertrain: str, battery_id, p19: pd.DataFrame,
            supplied: set[int] | None = None, log=None) -> dict[int, float]:
    """Return a copy of `gc` with the endogenous parameters computed.

    `gc` maps IDVP to value. Missing parameters count as zero: a component that
    does not exist in a vehicle is an explicit zero, never a silent gap.
    """
    g = dict(gc)
    supplied = supplied or set()

    def keep(idvp: int) -> bool:
        """A value that came with the source data outranks the equation.

        The reference vehicles are imported from the i3ET, whose columns carry
        hand-entered values that sometimes differ from its own formulas. For
        those, reproducing the model means honouring the value and recording the
        divergence. For a vehicle the user creates, nothing is supplied and every
        endogenous parameter is computed.
        """
        if idvp not in supplied:
            return False
        if log is not None:
            log.info("PARAM", f"IDVP {idvp} mantido como informado ({g.get(idvp)}); "
                              f"equacao nao aplicada")
        return True

    def v(idvp):
        x = g.get(idvp, 0.0)
        try:
            return float(x)
        except (TypeError, ValueError):
            return 0.0

    bat = _battery(p19, battery_id)

    # 9  — fA, plan area
    if not keep(9):
        g[9] = v(7) * v(8)

    # 15 — combined power: series hybrids run on the electric motor alone
    if not keep(15):
        g[15] = v(3) if powertrain in ("SHEV", "SPHEV") else max(v(2), v(3))

    # 29 — fH is exogenous; absent means 1, never 0, or fR would collapse
    if not v(29):
        g[29] = 1.0

    # 16 — fR, robustness
    if not keep(16):
        g[16] = v(15) * v(9) * v(14) * v(29)

    # 18 — electric starter
    if not keep(18):
        g[18] = 0.04 * v(2)

    # 28 — fB, body volume
    if not keep(28):
        g[28] = v(9) * v(27)

    # 33, 34, 36 — battery densities and reference capacity
    power_density = None if bat is None else bat["PowerDensity"]
    energy_density = None if bat is None else bat["EnergyDensity"]
    g[33] = float(power_density) if power_density not in (None, 0) and not _isnan(power_density) else 0.0
    g[34] = float(energy_density) if energy_density not in (None, 0) and not _isnan(energy_density) else 0.0
    ref_energy = None if bat is None else bat["RefEnergy"]
    g[36] = float(ref_energy) if ref_energy is not None and not _isnan(ref_energy) else 0.0

    # 35 — battery mass. Documento 1, secao 7.3: dimensioned by power when a
    # power density exists, by energy otherwise.
    if keep(35):
        pass
    elif not g[33]:
        g[35] = g[34] * v(5) if g[34] else 0.0
    else:
        g[35] = g[33] * (v(24) if v(24) > 0 else v(3))

    # 37 — ICE power per unit of hybrid complexity
    g[37] = v(2) / v(29) if v(29) else 0.0

    # 41, 42 — hybrid combination module: zero where the module does not exist
    if 41 not in gc or gc.get(41) in (None, ""):
        g[41] = 1.0 if powertrain in HYBRID_COMBINATION else 0.0
    g[42] = v(41) * v(15)

    if log is not None:
        for idvp in ENDOGENOUS:
            before = gc.get(idvp)
            if before is None:
                continue
            try:
                if abs(float(before) - float(g[idvp])) > 1e-9 * max(1.0, abs(float(g[idvp]))):
                    log.info("PARAM", f"IDVP {idvp} recalculado: {before} -> {g[idvp]}")
            except (TypeError, ValueError):
                pass
    return g


def _isnan(x) -> bool:
    try:
        return math.isnan(float(x))
    except (TypeError, ValueError):
        return True
