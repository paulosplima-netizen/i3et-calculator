"""Serie 1957-2025 do emplacamento por motorizacao, da aba Fleet Characteristics do i3EF.

Uso:  python tools/import_fleet_characteristics.py LCA_LV_i3EF_20261101.xlsx

Acrescenta a P72 (CSV de data/csv/fase_b) as linhas com SourceName = 'i3EF' (decisao 24 do B2,
23/11/2026): os anos anteriores a 2016, que o Anuario 2026 nao traz, valem (IsAdopted = 1);
2016-2025 ficam como comparacao (IsAdopted = 0), pois o Anuario mais recente prevalece.
Mapeamento (linha 11 da aba): automoveis e comerciais leves = Gasolina, Etanol, Flex, HEV,
PHEV, BEV, Diesel; caminhoes e onibus = Gasolina, Etanol, Eletrico, Gas, Diesel. A coluna
'Electrified' da 2.2.8 e a soma de HEV, PHEV e BEV; HEV do i3EF e um total (a 2.2.9 traz tres
hibridos). Valores arredondados ao inteiro. O Excel nao e alterado.
Rode depois de tools/import_anfavea.py (que regrava o CSV com as linhas da ANFAVEA).
"""

from __future__ import annotations

import csv
import os
import sys

import openpyxl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CSV = os.path.join(os.path.dirname(__file__), "..", "data", "csv", "fase_b",
                   "P72_FleetLicensingByPowertrain.csv")
SHEET = "Fleet Characteristics"
FIRST_ROW, LAST_YEAR, YEAR_COL = 12, 2025, 4
EDITION = "i3EF_20261101"
#: (classe, primeira coluna, [categorias da aba])
BLOCOS = [("Automobiles", 5, ["Gasoline", "Ethanol", "FlexFuel", "HEV", "PHEV", "BEV", "Diesel"]),
          ("LightCommercials", 12, ["Gasoline", "Ethanol", "FlexFuel", "HEV", "PHEV", "BEV",
                                    "Diesel"]),
          ("Trucks", 19, ["Gasoline", "Ethanol", "Electrified", "NaturalGas", "Diesel"]),
          ("Buses", 24, ["Gasoline", "Ethanol", "Electrified", "NaturalGas", "Diesel"])]
NOTA = ("Aba Fleet Characteristics do i3EF (linha do ano, arredondada); anos >= 2016 so para "
        "comparacao com o Anuario ANFAVEA 2026")


def linhas(xlsx: str) -> list[list]:
    ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)[SHEET]
    saida: list[list] = []
    for row in ws.iter_rows(min_row=FIRST_ROW, max_row=FIRST_ROW + 80, values_only=True):
        ano = row[YEAR_COL]
        if not isinstance(ano, (int, float)) or int(ano) > LAST_YEAR:
            continue
        ano = int(ano)
        adotada = 1 if ano < 2016 else 0
        for classe, c0, cats in BLOCOS:
            vals = {c: int(round(row[c0 + i] or 0)) for i, c in enumerate(cats)}
            if classe in ("Automobiles", "LightCommercials"):
                eletr = vals["HEV"] + vals["PHEV"] + vals["BEV"]
                fuel = {"Gasoline": vals["Gasoline"], "Ethanol": vals["Ethanol"],
                        "FlexFuel": vals["FlexFuel"], "Electrified": eletr,
                        "Diesel": vals["Diesel"]}
                eletrificados = {k: vals[k] for k in ("HEV", "PHEV", "BEV")}
            else:
                fuel, eletrificados = dict(vals), {}
            for dim, d in (("Fuel", fuel), ("Electrified", eletrificados)):
                for cat, un in d.items():
                    saida.append([ano, classe, dim, cat, un, adotada])
    return saida


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    with open(CSV, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh, delimiter=";")
        cab = rd.fieldnames
        base = [r for r in rd if r["SourceName"] != "i3EF"]
    tab = {"Fuel": "Fleet Characteristics (combustivel)",
           "Electrified": "Fleet Characteristics (eletrificados)"}
    for ano, classe, dim, cat, un, adot in linhas(argv[1]):
        base.append({"IDFP": 0, "SourceName": "i3EF", "SourceEdition": EDITION,
                     "SourceTable": tab[dim], "RefYear": ano, "VehicleClass": classe,
                     "Dimension": dim, "Category": cat, "Units": un, "IsAdopted": adot,
                     "NotesFP": NOTA})
    for i, r in enumerate(base, 1):
        r["IDFP"] = i
    with open(CSV, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=cab, delimiter=";")
        wr.writeheader()
        wr.writerows(base)
    print(f"P72: {len(base)} linhas ({sum(r['SourceName'] == 'i3EF' for r in base)} do i3EF)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
