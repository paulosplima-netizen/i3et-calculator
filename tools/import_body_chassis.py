"""Massas de referencia de carroceria e chassi e razao chassi/carroceria por receita: P63.

Fase B, bloco B1 (T38, validacao de massa). Cada uma das 68 receitas de P15
corresponde a uma coluna do bloco de receitas do M2 (T8:DD627). Nessa coluna:

    linha 54  massa do grupo A (carroceria), kg, digitada no M2
    linha 55  massa do grupo B (chassi sem bateria), kg, digitada no M2
    linha 627 "Parameter Chassi/Body weight" (ID 620): k = linha 55 / linha 54

As massas vem das alocacoes da planilha do GREET e nao das massas calculadas no
M1 (informacao do autor, 18/11/2026). A parcela da carroceria,
s = linha 54 / (linha 54 + linha 55), fica sempre entre 0 e 1 e e o padrao da
repartidora da diferenca de massa na T38. O k da planilha serve ao metodo
P69 = "Sim" (paridade) e passa de 1 em categorias com chassi mais pesado.

Blocos:
    BC1  colunas que definem cada receita (GREET, BISD e PBP_BISD)
    BC2  leitura das linhas 54, 55 e 627 e calculo da parcela
    BC3  gravacao do CSV (data/csv/fase_b/P63_RecipeBodyChassisMass.csv)

Uso:
    python tools/import_body_chassis.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import os
import re
import sys

import fase_a_common as common
from fase_a_common import num, open_workbook, text, write_csv
from import_recipes import ROW_NAME, ROW_RECIPE, SHEET, greet_recipes
from xlsx_cells import col2n, n2col

ROW_A, ROW_B, ROW_K = 54, 55, 627
COLS = ["IDVMR", "ColumnM2", "BodyMassRefKg", "ChassisMassRefKg",
        "ChassisBodyRatio", "BodyShareOfMassAdj", "SourceNote"]
NOTE = ("M2 linhas 54, 55 e 627; massas digitadas no M2, alocacao do GREET "
        "(informacao do autor, 18/11/2026)")
BISD_RE = re.compile(r"^(ICEV|HEV|SHEV|PHEV|BEV)-(PBP_)?(BISD\d+s?)$")


# --------------------------------------------------------------------------
# BLOCO BC1 -- coluna que define cada receita
#   Devolve : {IDVMR: coluna} para as 68 receitas de P15
# --------------------------------------------------------------------------
def recipe_columns(g) -> dict[str, int]:
    out = dict(greet_recipes(g))
    for c in range(col2n("CB"), col2n("DD") + 1):
        nome = text(g.get((ROW_NAME, c)))
        if nome and nome == text(g.get((ROW_RECIPE, c))):
            m = BISD_RE.match(nome)
            if m:
                prefixo = "PBP_" if m.group(2) else ""
                out[prefixo + m.group(3)] = c
    return out


# --------------------------------------------------------------------------
# BLOCO BC2 -- massas, razao e parcela
# --------------------------------------------------------------------------
def build(g) -> list[dict]:
    linhas = []
    for idvmr, c in sorted(recipe_columns(g).items()):
        a, b, k = num(g.get((ROW_A, c))), num(g.get((ROW_B, c))), num(g.get((ROW_K, c)))
        if not a or not b or k is None:
            raise SystemExit(f"{idvmr}: linhas 54, 55 ou 627 ausentes na coluna {n2col(c)}")
        linhas.append({"IDVMR": idvmr, "ColumnM2": n2col(c), "BodyMassRefKg": a,
                       "ChassisMassRefKg": b, "ChassisBodyRatio": k,
                       "BodyShareOfMassAdj": a / (a + b), "SourceNote": NOTE})
    return linhas


# --------------------------------------------------------------------------
# BLOCO BC3 -- gravacao
# --------------------------------------------------------------------------
def main(argv) -> int:
    g = open_workbook(argv).grid(SHEET)
    linhas = build(g)
    common.CSV_DIR = os.path.join(common.REPO, "data", "csv", "fase_b")
    write_csv("P63_RecipeBodyChassisMass", COLS, linhas)
    acima = [r["IDVMR"] for r in linhas if r["ChassisBodyRatio"] > 1]
    print(f"{len(linhas)} receitas; razao chassi/carroceria > 1 em {len(acima)}: {', '.join(acima)}")
    return 0 if len(linhas) == 68 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
