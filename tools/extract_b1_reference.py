"""Valores de referencia do bloco B1, lidos da planilha sem alterar nada.

Fase B, B1. A planilha e a fonte de verdade: o teste de paridade compara o
nucleo com estes valores. O arquivo e gravado em tests/fixtures/b1_reference.json
e e autossuficiente (entradas, fatores e resultados da planilha).

Conteudo:
    m2_columns             por coluna do M2 com resultado em T511: nome, receita,
                           chave de reposicao (P495), massa por grupo (linhas 69 a 81),
                           reposicoes (495 a 501), fim de vida (509), montagem (510),
                           total (511) e as parcelas que o compoem (516, 560, 571, 617)
    br23_control_panel     parametros das rotas da BR23 e do fim de vida (Control Panel)
    emission_factors_br    regiao da guia Emission Factors BR (aco e aluminio da BR23)
    mass_calibration       massas A e B (linhas 70, 71, 628, 629), k (linha 627) e
                           massa declarada (linha 35) das colunas SV1 a SV4

Uso:
    python tools/extract_b1_reference.py [caminho/para/LCA_LV_i3ET_20261119.xlsx]
"""

from __future__ import annotations

import json
import os
import sys

from fase_a_common import REPO, WORKBOOK_NAME, open_workbook, text
from xlsx_cells import col2n, n2col

OUT = os.path.join(REPO, "tests", "fixtures", "b1_reference.json")
M2 = "M2 GHG Mfg Module"
CP = "i3ET Control Panel"
EFBR = "Emission Factors BR"
ROWS_M2 = [35, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 495, 496, 497, 498,
           499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 516, 560,
           571, 617, 627, 628, 629, 15, 662, 705, 707, 708]
SV_COLS = ["FD", "FE", "FF", "FG"]


def _val(v):
    return v if isinstance(v, (int, float, str, bool)) else None


def m2_columns(g) -> dict:
    out = {}
    for c in range(col2n("T"), col2n("FG") + 1):
        t511 = g.get((511, c))
        if not isinstance(t511, float):
            continue
        out[n2col(c)] = {
            "name": text(g.get((8, c))), "recipe": text(g.get((9, c))),
            "powertrain": text(g.get((10, c))), "switch_P495": text(g.get((495, col2n("P")))),
            "rows": {str(r): _val(g.get((r, c))) for r in ROWS_M2 if g.get((r, c)) is not None},
        }
    return out


def control_panel(g) -> dict:
    cells = ([f"Z{r}" for r in range(91, 103)] + [f"P{r}" for r in range(123, 134)]
             + ["X74", "Z74", "X76", "Z76", "X77", "Z77"])
    return {a: _val(g.get((int("".join(ch for ch in a if ch.isdigit())),
                          col2n("".join(ch for ch in a if ch.isalpha()))))) for a in cells}


def region(g, rows, c1, c2) -> dict:
    out = {}
    for r in rows:
        for c in range(col2n(c1), col2n(c2) + 1):
            v = g.get((r, c))
            if v is not None:
                out[f"{n2col(c)}{r}"] = _val(v)
    return out


def main(argv) -> int:
    wb = open_workbook(argv)
    m2, cp, ef = wb.grid(M2), wb.grid(CP), wb.grid(EFBR)
    data = {
        "source_workbook": os.path.basename(argv[1]) if len(argv) > 1 else WORKBOOK_NAME,
        "note": "Valores em cache da planilha; nao recalculados. Gerado por tools/extract_b1_reference.py.",
        "m2_columns": m2_columns(m2),
        "br23_control_panel": control_panel(cp),
        "emission_factors_br": region(ef, range(1, 31), "A", "BK"),
        "mass_calibration": {
            c: {"k": m2.get((627, col2n(c))), "declared_row35": m2.get((35, col2n(c))),
                "A_est": m2.get((70, col2n(c))), "B_est": m2.get((71, col2n(c))),
                "A_sheet": m2.get((628, col2n(c))), "B_sheet": m2.get((629, col2n(c))),
                "calc_row69": m2.get((69, col2n(c)))} for c in SV_COLS},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(f"{len(data['m2_columns'])} colunas do M2; {len(data['emission_factors_br'])} celulas EF BR; "
          f"-> {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
