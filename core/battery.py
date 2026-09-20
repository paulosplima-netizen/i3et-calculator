"""Traction battery: two ways to reach the same number.

Documento 1, secao 11.5. Some battery models publish a material composition;
others publish only a carbon intensity per kilogram. The i3ET chooses between
the two by testing whether the model identifier starts with "PB", which would
break the moment a model is renamed. Here the choice is a declared column,
`P19.GHGMethod`, and it is anchored in what data actually exists.
"""

from __future__ import annotations

import pandas as pd

from .materials import emissions_for

IPRINC = "Iprinc"
IDVP_BATTERY_MASS = 35


def model_of(p19: pd.DataFrame, battery_id):
    if battery_id in (None, "", "-", "NA"):
        return None
    hit = p19[p19["IDBMd"] == battery_id]
    return None if hit.empty else hit.iloc[0]


def by_material(p19: pd.DataFrame, p20: pd.DataFrame, p09: pd.DataFrame,
                ef_table: pd.DataFrame, gc: dict[int, float], *,
                battery_id, idefv: str, log=None) -> pd.DataFrame:
    """C06 joined with C07: mass and emissions of the traction battery."""
    empty = pd.DataFrame(columns=["IDBMd", "IDGG", "IDM", "DsM", "BMshareGG",
                                  "MassIDMpGGB", "Quantity", "EF", "GHGIDMpGGB",
                                  "HasFactor", "CountsAsMass"])
    mass_total = float(gc.get(IDVP_BATTERY_MASS, 0.0) or 0.0)
    model = model_of(p19, battery_id)
    if model is None:
        if battery_id in (None, "", "-", "NA"):
            return empty
        # The vehicle declares a battery the base does not describe. Returning
        # nothing would charge it zero emissions, which is the one thing this
        # project does not do with missing data: the mass is kept, the factor
        # is declared absent, and the coverage report counts it.
        if log is not None:
            log.warn("C07", f"modelo de bateria {battery_id} ausente de P19; "
                            f"{mass_total:.3f} kg entram no total de massa sem "
                            f"fator de emissao")
        if mass_total == 0:
            return empty
        return pd.DataFrame([{
            "IDBMd": battery_id, "IDGG": IPRINC, "IDM": None,
            "DsM": f"Bateria de tracao {battery_id} (modelo ausente da base)",
            "BMshareGG": 1.0, "MassIDMpGGB": mass_total, "Quantity": mass_total,
            "EF": None, "GHGIDMpGGB": 0.0, "HasFactor": 0, "CountsAsMass": 1,
        }])

    method = model.get("GHGMethod") or "composition"

    if method == "none" or mass_total == 0:
        return empty

    if method == "gravimetric":
        intensity = model.get("GravimetricGHGDensity")
        if intensity is None or pd.isna(intensity):
            if log is not None:
                log.error("C07", f"bateria {battery_id} usa o caminho gravimetrico "
                                 f"mas nao tem GravimetricGHGDensity")
            return empty
        return pd.DataFrame([{
            "IDBMd": battery_id, "IDGG": IPRINC, "IDM": None,
            "DsM": "Bateria de tracao (intensidade de carbono massica)",
            "BMshareGG": 1.0, "MassIDMpGGB": mass_total, "Quantity": mass_total,
            "EF": float(intensity), "GHGIDMpGGB": mass_total * float(intensity),
            "HasFactor": 1, "CountsAsMass": 1,
        }])

    recipe = p20[p20["IDBMd"] == battery_id]
    if recipe.empty:
        if log is not None:
            log.error("C06", f"bateria {battery_id} declarada com composicao "
                             f"mas sem linhas em P20")
        return empty

    df = (recipe.merge(p09[["IDM", "DsM", "EFBasis", "EFBasisParam", "ShareRole"]],
                       on="IDM", how="left")
                .merge(ef_table[ef_table["IDEFV"] == idefv][["IDM", "EF"]],
                       on="IDM", how="left"))
    out = []
    for _, r in df.iterrows():
        qty = mass_total * float(r["BMshareGG"])
        ghg, has_factor = emissions_for(r, qty, gc, r.get("EF"))
        counts = (r.get("ShareRole") == "material")
        out.append({
            "IDBMd": battery_id, "IDGG": r["IDGG"], "IDM": r["IDM"],
            "DsM": r.get("DsM"), "BMshareGG": float(r["BMshareGG"]),
            "MassIDMpGGB": qty if counts else 0.0, "Quantity": qty,
            "EF": r.get("EF"), "GHGIDMpGGB": ghg,
            "HasFactor": int(has_factor), "CountsAsMass": int(counts),
        })
    return pd.DataFrame(out)
