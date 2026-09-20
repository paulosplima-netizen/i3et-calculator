"""Mass by subgroup and by GREET group.

Documento 1, secoes 8 and 9.
"""

from __future__ import annotations

import pandas as pd

IPRINC = "Iprinc"          # traction battery: mass comes from GC(35), not from scaling
IDVP_BATTERY_MASS = 35


def by_subgroup(p06: pd.DataFrame, p08: pd.DataFrame, gc: dict[int, float], *,
                idmpv: int, powertrain: str, log=None) -> pd.DataFrame:
    """C01 — one row per subgroup, carrying the inputs beside the result.

        ME = MR * (GC / GCR) ** Beta * fLM

    Any indeterminacy yields ME = 0 and an entry in the log, reproducing the
    IFERROR of the spreadsheet: silence is what we are trying to avoid.
    """
    params = p06[p06["IDMPV"] == idmpv].merge(p08, on="IDSG", how="inner")
    rows = []
    for _, r in params.iterrows():
        idsg, idvp = int(r["IDSG"]), int(r["IDVP"])
        excluded = str(r.get("ExcludedVPT") or "")
        applies = powertrain not in [x.strip() for x in excluded.split(",") if x.strip()]
        value = float(gc.get(idvp, 0.0) or 0.0) if applies else 0.0
        beta, gcr, mr = float(r["Beta"]), float(r["GCR"]), float(r["MR"])
        flm = float(r["fLM"])
        try:
            me = mr * ((value / gcr) ** beta) * flm if gcr else 0.0
        except (ValueError, ZeroDivisionError, OverflowError):
            me = 0.0
            if log is not None:
                log.warn("C01", f"subgrupo {idsg}: ME indeterminado "
                                f"(GC={value}, GCR={gcr}, Beta={beta})")
        if beta == 0 and value == 0 and me and log is not None:
            log.warn("C01", f"subgrupo {idsg}: Beta = 0 com GC = 0 atribui "
                            f"{me:.3f} kg a um componente inexistente")
        rows.append({"IDSG": idsg, "IDGG": r["IDGG"], "IDVP": idvp, "GC": value,
                     "Beta": beta, "GCR": gcr, "MR": mr, "fLM": flm, "ME": me})
    return pd.DataFrame(rows)


def by_group(c01: pd.DataFrame, gc: dict[int, float], groups: pd.DataFrame) -> pd.DataFrame:
    """C02 — mass per GREET group.

    The traction battery is the exception: its mass is not the sum of scaled
    subgroups but GC(35), obtained from the battery's energy or power density.
    Summing it from C01 as well would count it twice.
    """
    totals = (c01[c01["IDGG"] != IPRINC]
              .groupby("IDGG", as_index=False)["ME"].sum()
              .rename(columns={"ME": "MassIDGG"}))
    known = set(totals["IDGG"])
    extra = [{"IDGG": g, "MassIDGG": 0.0}
             for g in groups["IDGG"] if g not in known and g != IPRINC]
    battery = [{"IDGG": IPRINC, "MassIDGG": float(gc.get(IDVP_BATTERY_MASS, 0.0) or 0.0)}]
    return pd.concat([totals, pd.DataFrame(extra), pd.DataFrame(battery)],
                     ignore_index=True)
