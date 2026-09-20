"""Compare the calculation core against the i3ET fixtures.

This is the acceptance criterion of Documento 1, secao 17.1, run as a script so
the numbers can be read while the core is being built. The pytest version lives
in tests/test_i3et_reference.py.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core import calc, loader

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "i3et_reference.json")
DB = os.path.join(REPO, "data", "base_referencia.sqlite")

IDVP_BATTERY_ID = 32
TOL = 1e-6


def rel(a, b):
    if a is None or b is None:
        return None
    return abs(a - b) / max(abs(b), 1e-12)


def main(limit=None, verbose=False):
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    base = loader.load_sqlite(DB)

    # The fixture carries the factors the spreadsheet was set to; use them, so
    # the comparison is of the engine and not of the data.
    ef = pd.DataFrame(
        [{"IDM": m, "IDEFV": "FIXTURE", "EF": v, "EFnotes": "i3ET", "IsUserDefined": 0}
         for m, v in fx["ef_by_material"].items()])

    d02 = base["D02"].iloc[0]
    rows = []
    for code in fx["usable_configs"][:limit]:
        cfg = fx["configs"][code]
        gc = {int(k): (v if isinstance(v, (int, float)) else 0.0)
              for k, v in cfg["gc"].items()}
        battery_id = cfg["gc"].get(str(IDVP_BATTERY_ID))
        battery_id = None if battery_id in (None, "-", "NA") else str(battery_id).strip()
        # The i3ET columns carry hand-entered values for some endogenous
        # parameters; honouring them is what reproducing the model means.
        from core import params as _params
        supplied = {idvp for idvp in _params.ENDOGENOUS
                    if isinstance(cfg["gc"].get(str(idvp)), (int, float))}
        try:
            r = calc.calculate_vehicle(
                base, gc, powertrain=cfg["powertrain"], battery_id=battery_id,
                idmpv=int(d02["IDMPV"]), idvmr=d02["IDVMR"], idefv="FIXTURE",
                idapv="A-EF", boundary="MAT", ef_table=ef, supplied=supplied)
        except Exception as exc:                      # noqa: BLE001
            rows.append({"config": code, "erro": f"{type(exc).__name__}: {exc}"})
            continue
        exp = cfg["expected"]
        rows.append({
            "config": code,
            "powertrain": cfg["powertrain"],
            "massa_nossa": r["totals"]["MassIDV"],
            "massa_i3et": exp["vehicle_mass_kg"],
            "d_massa": rel(r["totals"]["MassIDV"], exp["vehicle_mass_kg"]),
            "bateria_nossa": float(r["C02"].set_index("IDGG").loc["Iprinc", "MassIDGG"]),
            "bateria_i3et": exp["mass_by_group_kg"].get("Iprinc"),
            "sem_fator_%": 100 * r["totals"]["ShareNoFactor"],
            "erro": "",
        })
    df = pd.DataFrame(rows)
    ok = df[df["erro"] == ""] if "erro" in df else df
    print(f"{len(df)} configuracoes, {len(ok)} calculadas sem excecao\n")
    if "d_massa" in ok and len(ok):
        bons = (ok["d_massa"] < TOL).sum()
        print(f"massa do veiculo dentro de {TOL:g}: {bons} de {len(ok)}")
        print(f"   erro relativo: mediana {ok['d_massa'].median():.3e}, "
              f"maximo {ok['d_massa'].max():.3e}\n")
        pd.set_option("display.width", 160)
        cols = ["config", "powertrain", "massa_nossa", "massa_i3et", "d_massa",
                "bateria_nossa", "bateria_i3et", "sem_fator_%"]
        print(ok[cols].head(14).to_string(index=False,
              float_format=lambda x: f"{x:,.4f}" if abs(x) > 1e-3 else f"{x:.2e}"))
    ruins = df[df["erro"] != ""] if "erro" in df else df.iloc[0:0]
    if len(ruins):
        print(f"\n{len(ruins)} com excecao:")
        for _, r in ruins.head(5).iterrows():
            print("  ", r["config"], r["erro"][:150])
    return df


if __name__ == "__main__":
    main()
