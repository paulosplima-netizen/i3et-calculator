"""Mass and emissions per material.

Documento 1, secoes 10 and 12. The recipes mix three kinds of row, and telling
them apart is what keeps the totals honest:

    material   a real mass fraction; contributes mass and emissions
    breakdown  redetails a material already counted (cathode chemistry);
               contributes emissions only, never mass
    process    a pseudo-material (assembly, disposal); its "share" is a
               conversion coefficient, and its factor may be per kWh or per
               vehicle rather than per kg
"""

from __future__ import annotations

import pandas as pd

IPRINC = "Iprinc"


def _quantity(mass_group: float, share: float) -> float:
    return mass_group * share


def emissions_for(row, quantity: float, gc: dict[int, float], ef) -> tuple[float, bool]:
    """Emissions of one material line, and whether a factor was available.

    The basis of the factor decides what it multiplies:
      mass     kg CO2e per kg      -> the quantity itself
      energy   kg CO2e per kWh     -> a vehicle parameter, e.g. battery capacity
      vehicle  kg CO2e per vehicle -> the factor alone
    """
    if ef is None or pd.isna(ef):
        return 0.0, False
    basis = row.get("EFBasis", "mass")
    if basis == "vehicle":
        return float(ef), True
    if basis == "energy":
        idvp = row.get("EFBasisParam")
        if idvp is None or pd.isna(idvp):
            return 0.0, False
        return float(gc.get(int(idvp), 0.0) or 0.0) * float(ef), True
    return quantity * float(ef), True


def by_material_group(c02: pd.DataFrame, p16: pd.DataFrame, p09: pd.DataFrame,
                      ef_table: pd.DataFrame, gc: dict[int, float], *,
                      idvmr: str, idefv: str, log=None) -> pd.DataFrame:
    """C03 joined with C04: mass and emissions per material per group."""
    recipe = p16[p16["IDVMR"] == idvmr]
    recipe = recipe[recipe["IDGG"] != IPRINC]
    if recipe.empty and log is not None:
        log.error("C03", f"receita {idvmr} sem linhas")

    df = (recipe.merge(c02, on="IDGG", how="inner")
                .merge(p09[["IDM", "DsM", "EFBasis", "EFBasisParam", "ShareRole"]],
                       on="IDM", how="left")
                .merge(ef_table[ef_table["IDEFV"] == idefv][["IDM", "EF"]],
                       on="IDM", how="left"))

    out = []
    for _, r in df.iterrows():
        qty = _quantity(float(r["MassIDGG"]), float(r["MshareGG"]))
        ghg, has_factor = emissions_for(r, qty, gc, r.get("EF"))
        counts_as_mass = (r.get("ShareRole") == "material")
        out.append({
            "IDGG": r["IDGG"], "IDM": r["IDM"], "DsM": r.get("DsM"),
            "ShareRole": r.get("ShareRole"), "MshareGG": float(r["MshareGG"]),
            "MassIDMpGG": qty if counts_as_mass else 0.0,
            "Quantity": qty,
            "EF": r.get("EF"), "GHGIDMpGG": ghg,
            "HasFactor": int(has_factor),
            "CountsAsMass": int(counts_as_mass),
        })
    return pd.DataFrame(out)


def by_group(c03: pd.DataFrame) -> pd.DataFrame:
    """C05 — emissions per group, materials only (the battery is elsewhere)."""
    return (c03.groupby("IDGG", as_index=False)["GHGIDMpGG"].sum()
               .rename(columns={"GHGIDMpGG": "GHGIDGG"}))
