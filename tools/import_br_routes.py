"""Fixtures do B1: itens de reposicao (P31, P31b, P32) e rotas da BR23 (P61, P62).

Fase B, bloco B1 (T16 e T17). Os itens de reposicao vem das decisoes do autor
(18/11/2026, intervalos aprovados); as rotas da BR23, da guia 'Emission Factors
BR' da planilha, linhas 11 (aco), 14 (ferro fundido), 18 (aluminio de chapa) e
20 (aluminio extrudado).

Blocos:
    BR1  itens de reposicao (constantes aprovadas) -> P31, P31b, P32
    BR2  fatores por rota e perdas, lidos da guia -> P61
    BR3  participacoes das rotas e da fracao importada -> P62
    BR4  gravacao dos CSV em data/csv/fase_b

Expressoes de P62 (RuleExpr): aritmetica com numeros, parametros do painel
(X91 a X101) e participacoes ja definidas, escritas [IDM:ROTA].

Uso:
    python tools/import_br_routes.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import csv
import os
import sys

from fase_a_common import open_workbook
from xlsx_cells import col2n

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "csv", "fase_b")
SHEET = "Emission Factors BR"
SRC_OK = "Decisao do autor, 18/11/2026"

# -- BR1 -------------------------------------------------------------------
P31_COLS = ["IDMI", "DsMI", "ItemKind", "IDGG", "IDM", "IntervalKm", "IntervalSource",
            "RefCount", "MassPerUnitKg", "NotesMI"]
P31 = [
    ("TIRE", "Tire set (4 tires)", "PART", "K", None, 40000, "i3ET-compatible", 4, 9.0718,
     "M2 T496: 4 jogos de 20 lb; 1/3 aco (IDM 1), 2/3 borracha (IDM 11)"),
    ("BATT_AUX", "Auxiliary lead-acid battery", "BATTERY", "Iaux", None, 70000, "Entered", 2,
     None, "M2 T499: 2 reposicoes; intervalo escolhido pelo autor"),
    ("BATT_TRAC", "Traction battery", "BATTERY", "Iprinc", None, 150000, "Entered", 1,
     None, "M2 T500: so com 'Sim Bat'; intervalo escolhido pelo autor"),
    ("FLD_77", "Engine oil", "FLUID", "K", "77", 5000, "i3ET-compatible", 39, None, "M2 T501"),
    ("FLD_78", "Power steering fluid", "FLUID", "K", "78", None, "i3ET-compatible", 0, None,
     "Sem reposicao na planilha; item inativo, ativavel pelo usuario"),
    ("FLD_79", "Brake fluid", "FLUID", "K", "79", 50000, "i3ET-compatible", 3, None, "M2 T501"),
    ("FLD_80", "Transmission fluid", "FLUID", "K", "80", 100000, "i3ET-compatible", 1, None,
     "M2 T501"),
    ("FLD_81", "Powertrain coolant", "FLUID", "K", "81", 50000, "i3ET-compatible", 3, None,
     "M2 T501"),
    ("FLD_82", "Windshield fluid", "FLUID", "K", "82", 10000, "i3ET-compatible", 19, None,
     "M2 T501"),
    ("FLD_83", "Adhesives", "FLUID", "K", "83", None, "i3ET-compatible", 0, None,
     "Sem reposicao na planilha; item inativo, ativavel pelo usuario"),
]
P31B_COLS = ["IDMI", "IDM", "Share", "NotesMPS"]
P31B = [("TIRE", "1", 1 / 3, "i3ET: jogo de 20 lbm, aco"),
        ("TIRE", "11", 2 / 3, "i3ET: jogo de 20 lbm, borracha")]
P32_COLS = ["IDCM", "CorrectivePct", "Basis", "SourceCM"]
P32 = [(1, 0, "PART_MASS_SHARE", "extensao sem fonte (0 ate a calibracao do B6)")]

# -- BR2 e BR3 -------------------------------------------------------------
#: linha da guia por material
ROWS = {"1": 11, "3": 14, "4a": 18, "4b": 20}
#: coluna do FE por rota
ROUTE_FE = {"RECYCLED": "M", "VIRGIN_MAIN": "N", "VIRGIN_ALT": "O", "GREEN": "P"}
#: parametro do painel que da a perda nacional ajustada (None = constante da guia)
LOSS_PARAM = {"1": "X91", "3": None, "4a": "X97", "4b": "X97"}
IMP_COL = {"IMP_ICEV": "BK", "IMP_ICEV_SUV": "BL", "IMP_HEV": "BM", "IMP_PHEV": "BN",
           "IMP_BEV": "BO"}

#: regras das rotas: (regra, idcp, expressao)
ROUTE_RULES = {
    "1": {"RECYCLED": ("FORMULA", None, "(X92-0.1)/0.9"),
          "VIRGIN_ALT": ("PARAM", "X93", None),
          "GREEN": ("PARAM", "X94", None),
          "VIRGIN_MAIN": ("FORMULA", None, "1-[1:RECYCLED]-[1:VIRGIN_ALT]-[1:GREEN]")},
    "3": {"RECYCLED": ("PARAM", "X92", None),
          "VIRGIN_MAIN": ("FORMULA", None, "0.9*[1:VIRGIN_MAIN]"),
          "VIRGIN_ALT": ("FORMULA", None, "0.9*[1:VIRGIN_ALT]"),
          "GREEN": ("FORMULA", None, "0.9*[1:GREEN]")},
}
for _m in ("4a", "4b"):
    ROUTE_RULES[_m] = {"RECYCLED": ("PARAM", "X98", None),
                       "GREEN": ("PARAM", "X100", None),
                       "VIRGIN_MAIN": ("FORMULA", None, "(1-X98-X100)*X99"),
                       "VIRGIN_ALT": ("FORMULA", None, "(1-X98-X100)*(1-X99)")}
#: fracao importada do primeiro tipo de veiculo (ICEV hatch/sedan)
IMP_RULES = {"1": ("PARAM", "X95", None), "3": ("FORMULA", None, "X95/2"),
             "4a": ("PARAM", "X101", None)}


def _v(g, col, row):
    return g.get((row, col2n(col)))


def build(g) -> tuple[list[list], list[list]]:
    p61, p62 = [], []
    for idm, row in ROWS.items():
        cel = lambda c, r=row: _v(g, c, r)           # noqa: E731
        p_adj = LOSS_PARAM[idm]
        for route, col in ROUTE_FE.items():
            p61.append([idm, route, cel(col), cel("L"), cel("G"), cel("H"),
                        None if p_adj else cel("I"), p_adj, cel("J"), "Typed",
                        f"{SHEET}!{col}{row} (FE por rota), L{row} (FE 100% global); "
                        f"dados primarios e SimaPro, blocos AS:BD"])
        for route, (regra, idcp, expr) in ROUTE_RULES[idm].items():
            p62.append([idm, route, regra, idcp, None, expr, f"{SHEET}!BG{row}:BJ{row}"])
        for imp, col in IMP_COL.items():
            if imp == "IMP_ICEV" and idm in IMP_RULES:
                regra, idcp, expr = IMP_RULES[idm]
                p62.append([idm, imp, regra, idcp, None, expr, f"{SHEET}!{col}{row}"])
            else:
                p62.append([idm, imp, "CONSTANT", None, cel(col), None,
                            f"{SHEET}!{col}{row}"])
    return p61, p62


def _write(nome: str, cols: list[str], linhas: list[list]) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{nome}.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(cols)
        for linha in linhas:
            w.writerow(["" if c is None else (repr(c) if isinstance(c, float) else c)
                        for c in linha])


def main(argv) -> int:
    g = open_workbook(argv).grid(SHEET)
    p61, p62 = build(g)
    _write("P31_MaintenanceItem", P31_COLS, [list(r) for r in P31])
    _write("P31b_MaintenancePartShare", P31B_COLS, [list(r) for r in P31B])
    _write("P32_CorrectiveMaintenance", P32_COLS, [list(r) for r in P32])
    _write("P61_BRRouteFactor",
           ["IDM", "Route", "EFRoute", "EFGlobal", "LossGlobalAdjusted", "LossGlobalAdopted",
            "LossNationalAdjusted", "LossNationalAdjIDCP", "LossNationalAdopted", "Origin",
            "SourceRF"], p61)
    _write("P62_BRRouteShare",
           ["IDM", "Route", "ShareRule", "IDCP", "ShareValue", "RuleExpr", "SourceRS"], p62)
    print(f"P31 {len(P31)}, P31b {len(P31B)}, P32 {len(P32)}, P61 {len(p61)}, P62 {len(p62)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
