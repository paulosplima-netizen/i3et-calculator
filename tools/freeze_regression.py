"""Freeze the current results of the twelve project vehicles.

Documento 1, secao 17.2. The regression fixture is not a second opinion about
the right answer -- it is a record of the answer this version gives. Any later
change that moves a number has to move this file too, in the same commit, with
the reason in the message. That is the whole point: silent drift becomes
impossible.

Run it again only when a change is meant to move the results:

    python tools/freeze_regression.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import calc, loader  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
OUT = os.path.join(REPO, "tests", "fixtures", "regressao_bp.json")

#: The totals that are frozen. Intermediate tables are not: they are allowed to
#: be reorganised as long as what comes out of them does not change.
FIELDS = ("MassIDV", "GHGMaterials", "GHGAssembly", "GHGCradleToGate",
          "GHGperKg", "MassNoFactor", "ShareNoFactor")


def build() -> dict:
    base = loader.load_sqlite(DB)
    d01 = base["D01"].set_index("IDV")
    results = calc.calculate(base)

    vehicles = {}
    for (idv, idea), r in sorted(results.items()):
        t = r["totals"]
        vehicles[f"{idv}/{idea}"] = {
            "DsV": d01.loc[idv]["DsV"],
            "IDVPT": d01.loc[idv]["IDVPT"],
            "Boundary": t["Boundary"],
            "totals": {k: t[k] for k in FIELDS},
            "by_group": {str(r_.IDGG): [r_.MassIDGG, r_.GHGIDGG]
                         for r_ in r["C10"].itertuples()},
        }
    with open(DB, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return {"base_sha256": digest, "n_vehicles": len(vehicles),
            "fields": list(FIELDS), "vehicles": vehicles}


def main():
    data = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print(f"congelados {data['n_vehicles']} veiculos em {os.path.relpath(OUT, REPO)}")
    for code, v in data["vehicles"].items():
        t = v["totals"]
        print(f"  {v['DsV']:6s} {v['IDVPT']:5s} "
              f"massa={t['MassIDV']:9.3f} kg  "
              f"bercoportao={t['GHGCradleToGate']:11.3f} kg CO2e")


if __name__ == "__main__":
    main()
