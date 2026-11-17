"""Fatores de uso combinado arbitrados para igualar a planilha (P56).

Fase A, passo 4. Para cada configuracao cujas potencias a planilha gravou,
encontra o par (FatorICE, FatorEE) que reproduz a potencia combinada gravada:

    P_combinada = FatorICE * P_ICE + FatorEE * P_EE

Regras de arbitragem (decisao de 17/11/2026, docs/06 secao 6):
    - ICEV: (1; 0).  BEV, SHEV, SPHEV: (0; 1).  Tipo 'Fixed'.
    - HEV e PHEV: combinada = ICE + EE  -> (1; 1)   tipo 'Sum'
                  combinada = ICE       -> (1; 0)   tipo 'ICE'
                  combinada = EE        -> (0; 1)   tipo 'EE'
                  ICE = EE = combinada  -> (1; 0)   tipo 'Tie' (ambiguo)
                  nenhum dos tres       -> 'NoFit'  (vai ao relatorio)
    - todo par de HEV e PHEV e provisorio ate o fim da validacao.

Fonte: a tabela de saidas do Control Panel (CP_OUT_*), quando a configuracao
esta na rodada gravada; senao o bloco auxiliar da Market Vehicles (MV_AUX).

Blocos:
    CF1  leitura das potencias gravadas (CSV de P52)
    CF2  arbitragem
    CF3  gravacao de P56

Uso:
    python tools/fit_combined_power.py        (depois de extract_control_panel
                                               e import_market_vehicles)
"""

from __future__ import annotations

import csv
import os
import sys

from fase_a_common import CSV_DIR, write_csv

TOL = 1e-6
FIXED = {"ICEV": (1.0, 0.0), "SHEV": (0.0, 1.0), "SPHEV": (0.0, 1.0), "BEV": (0.0, 1.0)}
EC_ORDER = ["ICEV", "HEV", "SHEV", "PHEV", "SPHEV", "BEV"]


# --------------------------------------------------------------------------
# BLOCO CF1 -- leitura das potencias gravadas
#   Le      : P52_ExcelReferenceValue.*.csv
#   Devolve : {conjunto: {caso: {'ice', 'ee', 'comb', 'bat'}}}
#             'bat' (energia da bateria) so existe no bloco auxiliar.
# --------------------------------------------------------------------------
def read_references() -> dict[str, dict[str, dict[str, float]]]:
    out: dict[str, dict[str, dict[str, float]]] = {}
    ind = {"O10": "ice", "O11": "ee", "O12": "comb"}
    mp = {"2": "ice", "3": "ee", "15": "comb", "5": "bat"}
    for nome in sorted(os.listdir(CSV_DIR)):
        if not (nome.startswith("P52_ExcelReferenceValue") and nome.endswith(".csv")):
            continue
        with open(os.path.join(CSV_DIR, nome), encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                campo = ind.get(r["IDInd"]) or (mp.get(r["IDMP"]) if r["IDMP"] else None)
                if campo is None or r["Value"] == "":
                    continue
                if r["RefSet"] == "MV_AUX" and r["IDMP"] not in mp:
                    continue
                out.setdefault(r["RefSet"], {}).setdefault(r["CaseKey"], {})[campo] = \
                    float(r["Value"])
    return out


# --------------------------------------------------------------------------
# BLOCO CF2 -- arbitragem
#   Recebe  : motorizacao e as tres potencias.
#   Devolve : (FatorICE, FatorEE, tipo).
# --------------------------------------------------------------------------
def _eq(a: float, b: float) -> bool:
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def fit(powertrain: str, ice: float, ee: float, comb: float) -> tuple[float, float, str]:
    if powertrain in FIXED:
        k = FIXED[powertrain]
        ok = _eq(comb, k[0] * ice + k[1] * ee)
        return k[0], k[1], "Fixed" if ok else "NoFit"
    if _eq(ice, ee) and _eq(comb, ice):
        return 1.0, 0.0, "Tie"
    if _eq(comb, ice + ee):
        return 1.0, 1.0, "Sum"
    if _eq(comb, ice):
        return 1.0, 0.0, "ICE"
    if _eq(comb, ee):
        return 0.0, 1.0, "EE"
    return 1.0, 1.0, "NoFit"


def powertrain_of(case: str, ref: dict[str, float]) -> str:
    """Motorizacao do caso. EC: ordem do rotulo (A<cat><1-6>). FC: pelas potencias
    e pela energia da bateria (ICEV sem motor eletrico; BEV sem motor a combustao;
    PHEV com bateria de 4 kWh ou mais; HEV nos demais)."""
    if case.startswith("A") and len(case) == 3:
        return EC_ORDER[int(case[2]) - 1]
    if ref["ee"] == 0:
        return "ICEV"
    if ref["ice"] == 0:
        return "BEV"
    return "PHEV" if ref.get("bat", 0) >= 4 else "HEV"


def arbitrate() -> list[dict]:
    refs = read_references()
    saidas = {c: (v, conj) for conj in ("CP_OUT_EC", "CP_OUT_FC")
              for c, v in refs.get(conj, {}).items()}
    aux = refs.get("MV_AUX", {})
    rows = []
    for caso in sorted(set(saidas) | set(aux), key=lambda k: (k[0] != "A", k)):
        base, conj = saidas[caso] if caso in saidas else (aux[caso], "MV_AUX")
        if caso in aux:
            base.setdefault("bat", aux[caso].get("bat", 0.0))
        pt = powertrain_of(caso, base)
        k_ice, k_ee, tipo = fit(pt, base["ice"], base["ee"], base["comb"])
        nota = None
        if conj != "MV_AUX" and caso in aux:
            a = aux[caso]
            k2 = fit(pt, a["ice"], a["ee"], a["comb"])
            if k2[2] != tipo:
                nota = (f"The auxiliary block (MV_AUX) gives ICE {a['ice']:.2f}, EE "
                        f"{a['ee']:.2f}, combined {a['comb']:.2f} kW, which fits as "
                        f"{k2[2]}; the output table prevails.")
        rows.append({
            "CaseKey": caso, "IDVPT": pt, "RefSet": conj,
            "PowerICE": base["ice"], "PowerEE": base["ee"], "PowerCombined": base["comb"],
            "FactorICE": k_ice, "FactorEE": k_ee, "FitKind": tipo,
            "IsProvisional": 0 if tipo == "Fixed" else 1, "NotesCPF": nota})
    return rows


# --------------------------------------------------------------------------
# BLOCO CF3 -- gravacao
# --------------------------------------------------------------------------
HEADER = ["CaseKey", "IDVPT", "RefSet", "PowerICE", "PowerEE", "PowerCombined",
          "FactorICE", "FactorEE", "FitKind", "IsProvisional", "NotesCPF"]


def main() -> int:
    print("Fatores de uso combinado ->", "data/csv/fase_a")
    rows = arbitrate()
    write_csv("P56_CombinedPowerFit", HEADER, rows)
    from collections import Counter
    print("   ", dict(Counter((r["IDVPT"], r["FitKind"]) for r in rows
                               if r["IDVPT"] in ("HEV", "PHEV"))))
    for r in rows:
        if r["FitKind"] == "NoFit" or r["NotesCPF"]:
            print("   atencao:", r["CaseKey"], r["FitKind"], r["NotesCPF"] or "")
    return 1 if any(r["FitKind"] == "NoFit" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
