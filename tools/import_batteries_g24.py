"""Modelos de bateria do GREET 2024 (G24): linhas novas de P18, P19 e P20.

Bloco B0 da Fase B, item 4. A guia 'GREET Batteries Material List' do i3ET traz
um modelo por coluna (identificador na linha 4). A base da 0.9.0 tinha cinco
modelos do G22 e quatro do G23; aqui entram todos os do G24 (colunas FI:HV),
entre eles `G24-HEV-Ni-MH`, `G24-PHEV50-NMC111` e `G24-BEV300-NMC111`, que a
rodada gravada cita. Os modelos `avPB` (media generica) e os `PB-*-indefinido`
ficam de fora: os ultimos sao P58.

Mapeamento (o mesmo que a base ja usa em G22 e G23):
    P19  RefRange = linha 12, RefEnergy = 14, RefWeight = 70, PowerDensity = 5
         (kg/kW, so HEV e FCEV), RefPower = RefWeight / PowerDensity,
         EnergyDensity = 6 (kg/kWh), GravimetricEnergyDensity = 71/1000,
         GravimetricGHGDensity = 67, EnergyGHGDensity = 68, RefGHGIDBMd = 70 x 67.
    P20  grupo `Iprinc`; uma linha por material das linhas 19 a 66. O bloco das
         linhas 41 a 50 (aco, aluminio, cobre, plastico, e ferro fundido,
         magnesio, cobalto, niquel, terras raras e borracha) e o do Ni-MH; materiais
         repetidos somam. Celula vazia vale 0.

Blocos:
    GB1  localizar as colunas dos modelos G24
    GB2  linhas de P18, P19 e P20
    GB3  gravacao dos CSV

Uso:
    python tools/import_batteries_g24.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import csv
import os
import sys

from fase_a_common import CSV_DIR, num, open_workbook, text, write_csv
from xlsx_cells import col2n

SHEET = "GREET Batteries Material List"
FIRST, LAST = col2n("FI"), col2n("HV")
PT = {"FCV": "FCEV"}
MATERIAL_ROWS = list(range(19, 67))      # 19-40 e 41-50 (bloco do Ni-MH) e 51-66


def _idm(v) -> str | None:
    s = text(v)
    return s


def _existing(table: str, key: str) -> set[str]:
    with open(os.path.join(os.path.dirname(CSV_DIR), f"{table}.csv"),
              encoding="utf-8-sig", newline="") as fh:
        return {r[key] for r in csv.DictReader(fh, delimiter=";")}


# --------------------------------------------------------------------------
# BLOCO GB1 -- colunas dos modelos G24
# --------------------------------------------------------------------------
def models(g) -> dict[str, int]:
    out: dict[str, int] = {}
    for col in range(FIRST, LAST + 1):
        name = text(g.get((4, col)))
        if name and name.startswith("G24-") and name not in out:
            out[name] = col
    return out


# --------------------------------------------------------------------------
# BLOCO GB2 -- linhas
# --------------------------------------------------------------------------
def build(g, cols: dict[str, int]):
    techs = _existing("P18", "IDBTe")
    p18, p19, p20 = [], [], []
    for name, c in sorted(cols.items()):
        pt = text(g.get((7, c)))
        pt = PT.get(pt, pt)
        tech = text(g.get((16, c)))
        if tech not in techs:
            techs.add(tech)
            p18.append({"IDBTe": tech, "IDBTy": "Ni-MH" if tech == "Ni-MH" else "Li-Ion",
                        "DsBTe": f"Tecnologia {tech}, importada do GREET 2024"})
        weight, mci = num(g.get((70, c))), num(g.get((67, c)))
        # HEV e FCEV: bateria de potencia (linha 5, kg/kW; linha 6 = ND). A potencia de
        # referencia e a massa dividida por essa razao.
        power_density = num(g.get((5, c)))
        ref_power = weight / power_density if weight and power_density else None
        gravimetric = num(g.get((71, c)))
        p19.append({
            "IDBMd": name, "IDEFV": "G24", "IDVPT": pt, "IDBTe": tech,
            "RefRange": num(g.get((12, c))), "RefEnergy": num(g.get((14, c))),
            "RefPower": ref_power, "RefWeight": weight,
            "RefGHGIDBMd": weight * mci if weight is not None and mci is not None else None,
            "EnergyDensity": num(g.get((6, c))), "PowerDensity": power_density,
            "GravimetricEnergyDensity": gravimetric / 1000 if gravimetric else None,
            "GravimetricPowerDensity": None,
            "GravimetricGHGDensity": mci, "EnergyGHGDensity": num(g.get((68, c))),
            "GHGMethod": "composition",
            "DsBMd": f"GREET 2024, guia '{SHEET}', coluna {_letters(c)}",
        })
        # Um material pode aparecer em duas linhas (o bloco 41-50 repete aco, aluminio,
        # cobre e plastico para o Ni-MH): as participacoes somam, como na formula da
        # planilha (SUMPRODUCT de D19:D51).
        shares: dict[str, float] = {}
        for row in MATERIAL_ROWS:
            idm = _idm(g.get((row, 2)))
            if idm is None:
                continue
            shares[idm] = shares.get(idm, 0.0) + (num(g.get((row, c))) or 0.0)
        for idm, share in shares.items():
            p20.append({"IDBMd": name, "IDGG": "Iprinc", "IDM": idm, "BMshareGG": share})
    return p18, p19, p20


def _letters(c: int) -> str:
    from xlsx_cells import n2col
    return n2col(c)


# --------------------------------------------------------------------------
# BLOCO GB3 -- gravacao
# --------------------------------------------------------------------------
def main(argv) -> int:
    wb = open_workbook(argv)
    g = wb.grid(SHEET)
    cols = models(g)
    p18, p19, p20 = build(g, cols)
    h19 = ["IDBMd", "IDEFV", "IDVPT", "IDBTe", "RefRange", "RefEnergy", "RefPower", "RefWeight",
           "RefGHGIDBMd", "EnergyDensity", "PowerDensity", "GravimetricEnergyDensity",
           "GravimetricPowerDensity", "GravimetricGHGDensity", "EnergyGHGDensity",
           "GHGMethod", "DsBMd"]
    write_csv("P18_BatteryTechnology.greet.add", ["IDBTe", "IDBTy", "DsBTe"], p18)
    write_csv("P19_BatteryModel.greet.add", h19, p19)
    write_csv("P20_BatteryMaterialShare.greet.add", ["IDBMd", "IDGG", "IDM", "BMshareGG"], p20)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
