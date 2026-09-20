"""Totals, and the honesty of the totals.

Documento 1, secao 14. Besides adding things up, this module answers a question
the i3ET does not ask: how much of the vehicle's mass has no published emission
factor. A total that silently treats missing data as zero emissions is worse
than no total at all.
"""

from __future__ import annotations

import pandas as pd

IPRINC = "Iprinc"


def by_group(c02: pd.DataFrame, c03: pd.DataFrame, c07: pd.DataFrame) -> pd.DataFrame:
    """C10 — mass and emissions per GREET group, battery included."""
    ghg_materials = (c03.groupby("IDGG", as_index=False)["GHGIDMpGG"].sum()
                        .rename(columns={"GHGIDMpGG": "GHGIDGG"}))
    ghg_battery = (c07.groupby("IDGG", as_index=False)["GHGIDMpGGB"].sum()
                      .rename(columns={"GHGIDMpGGB": "GHGIDGG"})) if len(c07) else \
                  pd.DataFrame(columns=["IDGG", "GHGIDGG"])
    ghg = pd.concat([ghg_materials, ghg_battery], ignore_index=True)
    ghg = ghg.groupby("IDGG", as_index=False)["GHGIDGG"].sum()
    return c02.merge(ghg, on="IDGG", how="left").fillna({"GHGIDGG": 0.0})


def by_material(c03: pd.DataFrame, c07: pd.DataFrame) -> pd.DataFrame:
    """C11 — mass and emissions per material, vehicle and battery together."""
    a = c03[["IDM", "DsM", "MassIDMpGG", "GHGIDMpGG"]].rename(
        columns={"MassIDMpGG": "MassIDM", "GHGIDMpGG": "GHGIDM"})
    if len(c07):
        b = c07[["IDM", "DsM", "MassIDMpGGB", "GHGIDMpGGB"]].rename(
            columns={"MassIDMpGGB": "MassIDM", "GHGIDMpGGB": "GHGIDM"})
        a = pd.concat([a, b], ignore_index=True)
    return (a.groupby(["IDM"], as_index=False)
             .agg(DsM=("DsM", "first"), MassIDM=("MassIDM", "sum"),
                  GHGIDM=("GHGIDM", "sum")))


def coverage(c03: pd.DataFrame, c07: pd.DataFrame) -> tuple[float, float]:
    """Mass whose emission factor is missing, and its share of the total.

    Only rows that carry real mass are counted: a process pseudo-material has
    no mass to be uncovered.
    """
    frames = [c03[["MassIDMpGG", "HasFactor", "CountsAsMass"]].rename(
        columns={"MassIDMpGG": "m"})]
    if len(c07):
        frames.append(c07[["MassIDMpGGB", "HasFactor", "CountsAsMass"]].rename(
            columns={"MassIDMpGGB": "m"}))
    df = pd.concat(frames, ignore_index=True)
    real = df[df["CountsAsMass"] == 1]
    total = float(real["m"].sum())
    missing = float(real.loc[real["HasFactor"] == 0, "m"].sum())
    return missing, (missing / total if total else 0.0)


def by_vehicle(c10: pd.DataFrame, c13: pd.DataFrame, *, boundary: str,
               c03: pd.DataFrame, c07: pd.DataFrame) -> dict:
    """C12 and C14 — the vehicle totals and the cradle-to-gate result."""
    mass = float(c10["MassIDGG"].sum())
    ghg_materials = float(c10["GHGIDGG"].sum())
    ghg_assembly = float(c13["GHGAssembly"].sum()) if len(c13) else 0.0
    included_assembly = ghg_assembly if boundary == "MAT_ASM" else 0.0
    missing_mass, missing_share = coverage(c03, c07)
    return {
        "MassIDV": mass,
        "GHGIDV": ghg_materials,
        "GHGMaterials": ghg_materials,
        "GHGAssembly": ghg_assembly,
        "GHGCradleToGate": ghg_materials + included_assembly,
        "GHGperKg": (ghg_materials + included_assembly) / mass if mass else None,
        "MassNoFactor": missing_mass,
        "ShareNoFactor": missing_share,
        "Boundary": boundary,
    }
