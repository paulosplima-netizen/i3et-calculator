"""Regras de valor padrao dos parametros de veiculo: P49 e P35.

Fase A, passo 3. Le a matriz M257:AW299 da guia 'Market Vehicles': uma linha
por parametro, uma coluna por criterio. Cada celula preenchida vira uma regra.

Blocos:
    DR1  colunas da matriz -> criterios
    DR2  celulas da matriz -> regras, na ordem de precedencia
    DR3  porte pelo limite de area (parametro 44)
    DR4  versoes e gravacao dos CSV

Precedencia (a ordem em que as regras de um parametro sao avaliadas; vale a
primeira atendida): luxo; motorizacao; carroceria; faixa de potencia; porte;
carroceria x porte. E a leitura do levantamento de 10/11/2026: a matriz nao
declara a ordem, e esta e a que reproduz as descricoes dadas pelo autor para
o ar-condicionado (17) e a instrumentacao (22).

Uso:
    python tools/build_default_rules.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import sys

from fase_a_common import SIZE, num, open_workbook, text, write_csv
from xlsx_cells import addr, col2n, n2col

SHEET = "Market Vehicles"
C = col2n
ROW_LIMITS, ROW_HEAD = 258, 259
FIRST_ROW, LAST_ROW = 260, 299          # parametros 1 a 40
VERSION = "TAB"

#: Parametro cujo valor na matriz e um multiplicador de outro parametro.
FACTOR_OF = {18: 2}                     # partida = 0,03 x potencia do motor a combustao
#: Rotulo da matriz -> formula da potencia combinada.
POWER_FORMULA = {"ICE": "ICE", "BEE": "EE"}
#: Rotulo de carroceria da matriz -> carrocerias da base.
DESIGNS = {"Sedan/ Hatch": ["Sedan", "Hatchback"], "SUV": ["SUV"], "PUT": ["PUT"]}

P49_COLS = ["IDDRV", "DsDRV", "IsDefault", "NotesDRV"]
P35_COLS = ["IDDRV", "IDMP", "RuleSeq", "IDVPT", "IDVDT", "IDVS", "IDLR", "PowerMinHP",
            "PowerMaxHP", "AreaMin", "AreaMax", "Value", "ValueText", "FactorOfIDMP",
            "SourceCell"]


# --------------------------------------------------------------------------
# BLOCO DR1 -- colunas -> criterios
#   Le      : os cabecalhos das linhas 258 e 259
#   Devolve : lista de (coluna, [criterios]) na ordem de precedencia. Uma
#             coluna 'Sedan/ Hatch' gera dois criterios, um por carroceria.
# --------------------------------------------------------------------------
def criteria(g) -> list[tuple[int, list[dict]]]:
    lim1, lim2 = num(g[(ROW_LIMITS, C("Z"))]), num(g[(ROW_LIMITS, C("AA"))])
    faixas = {"Z": {"PowerMaxHP": lim1}, "AA": {"PowerMinHP": lim1, "PowerMaxHP": lim2},
              "AB": {"PowerMinHP": lim2}}
    ordem = [(C("AH"), [{"IDLR": "Luxury"}])]
    for c in range(C("P"), C("V") + 1):
        ordem.append((c, [{"IDVPT": text(g[(ROW_HEAD, c)])}]))
    for c in range(C("W"), C("Y") + 1):
        ordem.append((c, [{"IDVDT": d} for d in DESIGNS[text(g[(ROW_HEAD, c)])]]))
    for col, crit in faixas.items():
        ordem.append((C(col), [crit]))
    for c in range(C("AC"), C("AG") + 1):
        ordem.append((c, [{"IDVS": SIZE[text(g[(ROW_HEAD, c)])]}]))
    for c in range(C("AI"), C("AW") + 1):
        porte = SIZE[text(g[(ROW_HEAD, c)])]
        ordem.append((c, [{"IDVDT": d, "IDVS": porte}
                          for d in DESIGNS[text(g[(ROW_LIMITS, c)])]]))
    return ordem


# --------------------------------------------------------------------------
# BLOCO DR2 -- celulas -> regras
#   Le      : linhas 260 a 299; '-' significa "sem regra para este criterio"
#   Devolve : as regras, numeradas por parametro na ordem de precedencia
# --------------------------------------------------------------------------
def matrix_rules(g) -> list[dict]:
    ordem, out = criteria(g), []
    for r in range(FIRST_ROW, LAST_ROW + 1):
        n = num(g.get((r, C("M"))))
        if n is None:
            continue
        n, seq = int(n), 0
        for c, criterios in ordem:
            bruto = g.get((r, c))
            if bruto is None or bruto == "-":
                continue
            for crit in criterios:
                seq += 1
                regra = {"IDDRV": VERSION, "IDMP": n, "RuleSeq": seq, **crit,
                         "SourceCell": addr(r, c)}
                if isinstance(bruto, str):
                    regra["ValueText"] = POWER_FORMULA.get(bruto, bruto)
                else:
                    regra["Value"] = float(bruto)
                    # so as celulas de faixa de potencia trazem multiplicador
                    if "PowerMinHP" in crit or "PowerMaxHP" in crit:
                        regra["FactorOfIDMP"] = FACTOR_OF.get(n)
                out.append(regra)
    return out


# --------------------------------------------------------------------------
# BLOCO DR3 -- porte pela area (parametro 44)
#   Le      : limites em AC258:AF258 (m2) e rotulos em AC259:AG259
#   Devolve : cinco regras: area menor que cada limite; a ultima, sem limite
# --------------------------------------------------------------------------
def size_rules(g) -> list[dict]:
    out, anterior = [], None
    for seq, c in enumerate(range(C("AC"), C("AG") + 1), 1):
        limite = num(g.get((ROW_LIMITS, c)))
        out.append({"IDDRV": VERSION, "IDMP": 44, "RuleSeq": seq,
                    "AreaMin": anterior, "AreaMax": limite,
                    "ValueText": SIZE[text(g[(ROW_HEAD, c)])],
                    "SourceCell": f"{n2col(c)}{ROW_LIMITS}"})
        anterior = limite
    return out


# --------------------------------------------------------------------------
# BLOCO DR4 -- versoes e gravacao
# --------------------------------------------------------------------------
def main(argv) -> int:
    g = open_workbook(argv).grid(SHEET)
    print("Regras de valor padrao ->", "data/csv/fase_a")
    write_csv("P49_DefaultRuleVersion", P49_COLS, [
        {"IDDRV": "TAB", "DsDRV": "Regras como tabuladas em Market Vehicles M257:AW299",
         "IsDefault": 1,
         "NotesDRV": "Uma regra por celula preenchida da matriz. Precedencia: luxo, "
                     "motorizacao, carroceria, faixa de potencia, porte, carroceria x porte."},
        {"IDDRV": "FML", "DsDRV": "Valores que as formulas da planilha gravaram",
         "IsDefault": 0,
         "NotesDRV": "Sem linhas em P35: as formulas nao seguem a matriz em todos os "
                     "veiculos. O resultado delas esta em P27, na classe Def, e e contra "
                     "ele que a versao TAB e comparada."}])
    write_csv("P35_VehicleParamDefaultRule", P35_COLS, matrix_rules(g) + size_rules(g))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
