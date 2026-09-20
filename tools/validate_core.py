"""Acceptance report: the calculation core against the i3ET.

Documento 1, secao 17.1. Every configuration falls in exactly one of three
buckets, and the third one is the only one that matters:

    exata            reproduces the i3ET to 1e-6 relative
    leveza (M5)      differs by a single multiplicative factor applied to every
                     scaled subgroup -- the lightweighting factor, which belongs
                     to module M5 and is out of scope for v1
    sem explicacao   anything else: a real failure
"""

from __future__ import annotations

import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core import calc, loader
from core import params as P

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "i3et_reference.json")
DB = os.path.join(REPO, "data", "base_referencia.sqlite")

TOL = 1e-6
#: Subgroups that do not follow the scaling law, so they carry no fLM.
NOT_SCALED_BY = {35, 42}
IDSG_HYBRID_MODULE = 43

#: Divergences already investigated, explained and accepted by the author.
#: They belong in their own bucket so that "sem explicacao" keeps meaning
#: "something new broke" -- a check that is permanently amber stops being read.
KNOWN = {
    "modulo hibrido em FCV": (
        "O i3ET zera o modulo de combinacao hibrida para ICEV, BEV, SHEV, SPHEV, "
        "HFCEV e EFCEV, mas as configuracoes usam o rotulo FCV, ausente dessa lista. "
        "A calculadora atribui o modulo apenas a HEV e PHEV. Decisao de 20/09/2026: "
        "manter a regra coerente e registrar no Relatorio de Divergencias."),
}


def classify(code, cfg, result, p08):
    mass_ours = result["totals"]["MassIDV"]
    mass_i3et = cfg["expected"]["vehicle_mass_kg"]
    if abs(mass_ours - mass_i3et) <= TOL * max(1.0, abs(mass_i3et)):
        return "exata", None
    i3 = {int(k): v for k, v in cfg["expected"]["me_by_subgroup_kg"].items()}
    ours = {int(r.IDSG): r.ME for r in result["C01"].itertuples()}
    ratios = [i3[s] / ours[s] for s in ours
              if s in i3 and ours[s] > 1e-9 and i3[s] > 1e-9
              and p08.get(s) not in NOT_SCALED_BY]
    if ratios and (max(ratios) - min(ratios)) < 1e-9:
        factor = statistics.median(ratios)
        # A constant factor of 1 explains nothing: the subgroups agree and the
        # total does not, which means the difference is somewhere else.
        if abs(factor - 1.0) > 1e-9:
            return "leveza", factor

    # Known and accepted: the hybrid combination module in fuel cell vehicles.
    delta_module = ours.get(IDSG_HYBRID_MODULE, 0.0) - i3.get(IDSG_HYBRID_MODULE, 0.0)
    if cfg["powertrain"] == "FCV" and abs(delta_module - (mass_ours - mass_i3et)) < 1e-6:
        return "modulo hibrido em FCV", None

    return "sem explicacao", None


def main():
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    base = loader.load_sqlite(DB)
    ef = pd.DataFrame(
        [{"IDM": m, "IDEFV": "FIXTURE", "EF": v, "EFnotes": "i3ET", "IsUserDefined": 0}
         for m, v in fx["ef_by_material"].items()])
    p08 = {int(r.IDSG): int(r.IDVP) for r in base["P08"].itertuples()}
    idvmr = base["D02"].iloc[0]["IDVMR"]

    buckets = {"exata": [], "leveza": [], "modulo hibrido em FCV": [],
               "sem explicacao": []}
    for code in fx["usable_configs"]:
        cfg = fx["configs"][code]
        gc = {int(k): (v if isinstance(v, (int, float)) else 0.0)
              for k, v in cfg["gc"].items()}
        bid = cfg["gc"].get("32")
        bid = None if bid in (None, "-", "NA") else str(bid).strip()
        supplied = {i for i in P.ENDOGENOUS
                    if isinstance(cfg["gc"].get(str(i)), (int, float))}
        r = calc.calculate_vehicle(base, gc, powertrain=cfg["powertrain"],
                                   battery_id=bid, idmpv=1, idvmr=idvmr,
                                   idefv="FIXTURE", idapv="A-EF", boundary="MAT",
                                   ef_table=ef, supplied=supplied)
        bucket, factor = classify(code, cfg, r, p08)
        buckets[bucket].append((code, cfg["powertrain"], factor,
                                r["totals"]["MassIDV"],
                                cfg["expected"]["vehicle_mass_kg"]))

    n = len(fx["usable_configs"])
    print(f"VALIDACAO DO NUCLEO CONTRA O i3ET — {n} configuracoes\n")
    for name in ("exata", "leveza", "modulo hibrido em FCV", "sem explicacao"):
        print(f"  {name:16s}: {len(buckets[name]):3d}  ({100*len(buckets[name])/n:.0f}%)")
    fatores = sorted({round(f, 6) for _, _, f, _, _ in buckets["leveza"] if f})
    if fatores:
        print(f"\n  fatores de leveza: {fatores}")
    for name, texto in KNOWN.items():
        if buckets.get(name):
            print(f"\n  {name} — divergencia conhecida e aceita:")
            print(f"    {texto}")
            print(f"    configuracoes: {', '.join(c for c, *_ in buckets[name])}")
    if buckets["sem explicacao"]:
        print("\n  SEM EXPLICACAO:")
        for code, pt, _, a, b in buckets["sem explicacao"]:
            print(f"    {code:6s} {pt:5s} nossa={a:12.4f}  i3ET={b:12.4f}  "
                  f"dif={a-b:+10.4f}")
    print(f"\n  {'RESULTADO: aprovado' if not buckets['sem explicacao'] else 'RESULTADO: reprovado'}"
          f" — {len(buckets['sem explicacao'])} divergencia(s) sem explicacao")
    return buckets


if __name__ == "__main__":
    main()
