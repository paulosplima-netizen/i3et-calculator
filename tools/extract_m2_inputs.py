"""Entradas que o M2 usa nas seis configuracoes da rodada gravada (P52, RefSet M2_IN).

Fase A, passo 5. As colunas ET:EY do M2 sao o que a tabela de saidas do Control
Panel mostra. Varios parametros (ar-condicionado, motor de partida, area de vidros,
fator de utilidades) saem ali de formulas por faixa de potencia e porte, e nao
coincidem com o bloco auxiliar de Market Vehicles. A calculadora, ate ter as regras
de valor padrao ligadas, usa o que a planilha gravou.

Blocos:
    M2I1  leitura das colunas ET:EY, linhas 9 a 51
    M2I2  gravacao do CSV
"""

from __future__ import annotations

import sys

from fase_a_common import WORKBOOK_NAME, open_workbook, write_csv
from xlsx_cells import addr, col2n

SHEET = "M2 GHG Mfg Module"
COLS = dict(zip(["A01", "A02", "A03", "A04", "A05", "A06"],
                ["ET", "EU", "EV", "EW", "EX", "EY"]))
P52_COLS = ["RefSet", "CaseKey", "IDInd", "IDMP", "Value", "ValueText",
            "Workbook", "Sheet", "Cell"]
FIRST_ROW, LAST_ROW, IDX_COL = 9, 51, "P"
MAX_IDMP = 40


# --------------------------------------------------------------------------
# BLOCO M2I1 -- leitura
#   Le      : indice do parametro (coluna P) e valor de cada configuracao.
#   Devolve : linhas de P52 com IDMP preenchido e IDInd vazio.
# --------------------------------------------------------------------------
def read(argv) -> list[dict]:
    g = open_workbook(argv).grid(SHEET)
    out = []
    for row in range(FIRST_ROW, LAST_ROW + 1):
        idx = g.get((row, col2n(IDX_COL)))
        if not isinstance(idx, (int, float)) or not 0 < int(idx) <= MAX_IDMP:
            continue
        for case, col in COLS.items():
            v = g.get((row, col2n(col)))
            rec = {"RefSet": "M2_IN", "CaseKey": case, "IDInd": None, "IDMP": int(idx),
                   "Value": None, "ValueText": None, "Workbook": WORKBOOK_NAME,
                   "Sheet": SHEET, "Cell": addr(row, col2n(col))}
            if isinstance(v, (int, float)):
                rec["Value"] = float(v)
            elif v not in (None, "", "-", "ND"):
                rec["ValueText"] = str(v)
            else:
                continue
            out.append(rec)
    return out


def main(argv) -> int:
    rows = read(argv)
    write_csv("P52_ExcelReferenceValue.entradas_do_m", P52_COLS, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
