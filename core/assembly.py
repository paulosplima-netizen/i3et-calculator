"""Vehicle assembly.

Documento 1, secao 13. Three ways of obtaining the same quantity, declared in
`P23.Method`, so that a result always says where its assembly figure came from.
"""

from __future__ import annotations

import pandas as pd

IDM_ASSEMBLY = "99"          # "A - Assembling", factor given per vehicle
G_PER_KG = 1000.0


def ghg(p21: pd.DataFrame, p22: pd.DataFrame, p23: pd.DataFrame,
        p25: pd.DataFrame, ef_table: pd.DataFrame, *,
        idapv: str, idefv: str, log=None) -> pd.DataFrame:
    """C13 — assembly emissions, by process when the detail exists."""
    version = p23[p23["IDAPV"] == idapv]
    if version.empty:
        if log is not None:
            log.error("C13", f"versao de montagem {idapv} inexistente")
        return pd.DataFrame(columns=["IDAP", "DsAP", "EnergyPerVehicle", "GHGAssembly"])
    version = version.iloc[0]
    method = version["Method"]

    if method == "from_EF":
        hit = ef_table[(ef_table["IDM"] == IDM_ASSEMBLY) & (ef_table["IDEFV"] == idefv)]
        value = float(hit.iloc[0]["EF"]) if not hit.empty and pd.notna(hit.iloc[0]["EF"]) else 0.0
        if hit.empty and log is not None:
            log.warn("C13", f"sem fator de montagem (IDM 99) para a versao {idefv}")
        return pd.DataFrame([{"IDAP": 0, "DsAP": "Montagem (agregada, da tabela de fatores)",
                              "EnergyPerVehicle": 0.0, "GHGAssembly": value}])

    if method == "fixed":
        value = float(version["FixedGHGPerVehicle"] or 0.0)
        return pd.DataFrame([{"IDAP": 0, "DsAP": "Montagem (valor agregado da versao)",
                              "EnergyPerVehicle": 0.0, "GHGAssembly": value}])

    # method == "process"
    included = p21[p21["IncludedInA"] == 1][["IDAP", "DsAP"]]
    fuels = p25[p25["IDEFV"] == idefv][["IDFuel", "EFfuel"]]
    df = (p22[p22["IDAPV"] == idapv]
          .merge(included, on="IDAP", how="inner")
          .merge(fuels, on="IDFuel", how="left"))
    if df["EFfuel"].isna().any() and log is not None:
        faltam = sorted(set(df.loc[df["EFfuel"].isna(), "IDFuel"]))
        log.warn("C13", f"sem fator para os energeticos {faltam} na versao {idefv}")
    df["GHG"] = df["EnergyPerVehicle"] * df["FuelShare"] * df["EFfuel"].fillna(0.0) / G_PER_KG
    out = (df.groupby(["IDAP", "DsAP"], as_index=False)
             .agg(EnergyPerVehicle=("EnergyPerVehicle", "first"),
                  GHGAssembly=("GHG", "sum")))
    return out
