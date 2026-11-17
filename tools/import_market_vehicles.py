"""Fixtures da guia Market Vehicles: P54, P26, P27 e a parte auxiliar de P52.

Fase A, passo 3.

Blocos:
    MV1  catalogo dos 58 parametros          -> P54
    MV2  veiculos                            -> P26
    MV3  valores dos parametros por veiculo  -> P27, com a classe do valor
    MV4  bloco auxiliar B164:DC204           -> P52 (MV_AUX)
    MV5  gravacao dos CSV

Uso:
    python tools/import_market_vehicles.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import sys

from fase_a_common import DESIGN, SIZE, WORKBOOK_NAME, num, open_workbook, text, write_csv
from xlsx_cells import addr, col2n, n2col

SHEET = "Market Vehicles"
C = col2n
FIRST_ROW, LAST_ROW = 7, 161            # veiculos
AUX_FIRST, AUX_LAST = 165, 204          # 36 configuracoes equalizadas + 4 de livre escolha
COL_P1 = C("N")                         # parametro 1; o parametro n fica em N + n - 1
N_PARAMS = 58
SALES_YEAR = 2025

#: Parametros textuais (o resto e numerico).
TEXT_PARAMS = {1, 32, 41, 42, 43, 44, 45, 47, 51, 54, 58}
#: Parametros com regra de valor padrao em M257:AW299.
DEFAULT_PARAMS = {4, 13, 15, 17, 18, 22, 26, 29, 44}
#: Parametros que a planilha calcula a partir de outros.
CALC_PARAMS = {9, 16, 28, 30, 33, 35, 36, 37, 40, 41, 46, 50, 53, 55}
#: Parametros buscados no registro do PBEV.
PBEV_PARAMS = {45, 47}
#: Parametros do SELECAO que sao media ponderada (Control Panel AJ9:AJ18).
AVG_PARAMS = {2, 7, 8, 27, 14, 48, 49, 50, 52, 55}

P54_COLS = ["IDMP", "DsMP", "utMP", "SheetColumn", "IDVP", "ValueKind"]
P26_COLS = ["IDMV", "DsMV", "Brand", "Model", "IDVPT", "IDVDT", "IDVS", "IDLR", "Fuel",
            "MarketGroup", "SalesClass", "SalesRefYear", "SalesUnits", "IsSelecao",
            "IDMVRepresentative", "SheetRow", "NotesMV", "SourceMV"]
P27_COLS = ["IDMV", "IDMP", "Value", "ValueText", "ValueClass"]
P52_COLS = ["RefSet", "CaseKey", "IDInd", "IDMP", "Value", "ValueText",
            "Workbook", "Sheet", "Cell"]


def pcol(n: int) -> int:
    return COL_P1 + n - 1


def is_vehicle(g, r) -> bool:
    """A linha 113 e um separador; reconhece-se pela motorizacao 'X'."""
    return text(g.get((r, C("N")))) is not None and g.get((r, C("M"))) != "X"


# --------------------------------------------------------------------------
# BLOCO MV1 -- catalogo de parametros (P54)
#   Le      : linhas 4 (numero), 5 (nome) e 6 (unidade), colunas N:BS
#   Devolve : 58 linhas. IDVP aponta para P07 nos parametros 2 a 40, que tem
#             o mesmo numero e o mesmo significado nas duas tabelas.
# --------------------------------------------------------------------------
def market_params(g) -> list[dict]:
    out = []
    for n in range(1, N_PARAMS + 1):
        c = pcol(n)
        assert g.get((4, c)) == float(n), f"linha 4, coluna {n2col(c)}: esperado {n}"
        out.append({"IDMP": n, "DsMP": text(g.get((5, c))) or f"Parameter {n}",
                    "utMP": text(g.get((6, c))), "SheetColumn": n2col(c),
                    "IDVP": n if 2 <= n <= 40 else None,
                    "ValueKind": "Text" if n in TEXT_PARAMS else "Num"})
    return out


# --------------------------------------------------------------------------
# BLOCO MV2 -- veiculos (P26)
#   Le      : linhas 7 a 161. IDMV e a linha do veiculo na planilha.
#   Devolve : um registro por veiculo. O SELECAO se reconhece pelo nome; a
#             coluna I traz o veiculo representativo de que ele herda valores.
# --------------------------------------------------------------------------
def vehicles(g) -> list[dict]:
    linha_de = {text(g.get((r, C("N")))): r
                for r in range(FIRST_ROW, LAST_ROW + 1) if is_vehicle(g, r)}
    out = []
    for nome, r in linha_de.items():
        selecao = nome.startswith("SELEÇÃO")
        out.append({
            "IDMV": r, "DsMV": nome,
            "Brand": text(g.get((r, C("J")))), "Model": text(g.get((r, C("K")))),
            "IDVPT": text(g[(r, C("M"))]),
            "IDVDT": DESIGN[text(g[(r, pcol(42))])], "IDVS": SIZE[text(g[(r, pcol(44))])],
            "IDLR": text(g[(r, pcol(43))]), "Fuel": text(g.get((r, pcol(45)))),
            "MarketGroup": text(g.get((r, C("DF")))),
            "SalesClass": text(g.get((r, C("H")))) or "ND",
            "SalesRefYear": SALES_YEAR, "SalesUnits": num(g.get((r, C("L")))),
            "IsSelecao": int(selecao),
            "IDMVRepresentative": linha_de[text(g[(r, C("I"))])] if selecao else None,
            "SheetRow": r, "NotesMV": text(g.get((r, C("G")))),
            "SourceMV": f"{WORKBOOK_NAME}, {SHEET}"})
    return out


# --------------------------------------------------------------------------
# BLOCO MV3 -- valores por veiculo (P27)
#   Le      : N:BS de cada veiculo, e a marca de formula de cada celula
#   Devolve : um valor por veiculo e parametro preenchido, com a classe:
#               Man   digitado (dado do fabricante ou do levantamento)
#               Def   formula de valor padrao (parametros de DEFAULT_PARAMS)
#               Calc  formula de calculo
#               PBEV  buscado no registro do PBEV
#               Avg   media ponderada do SELECAO
#               Rep   copiado do veiculo representativo do SELECAO
#   Nota    : a planilha nao distingue estimativa de engenharia de dado do
#             fabricante; a classe Eng fica sem uso neste passo.
# --------------------------------------------------------------------------
def classify(n: int, tem_formula: bool, selecao: bool) -> str:
    if not tem_formula:
        return "Man"
    if selecao and n in AVG_PARAMS:
        return "Avg"
    if n in DEFAULT_PARAMS:
        return "Def"
    if n in CALC_PARAMS:
        return "Calc"
    if n in PBEV_PARAMS:
        return "PBEV"
    return "Rep" if selecao else "Calc"


def vehicle_values(g, formulas, veiculos) -> list[dict]:
    out = []
    for v in veiculos:
        r = v["IDMV"]
        for n in range(1, N_PARAMS + 1):
            bruto = g.get((r, pcol(n)))
            if n in TEXT_PARAMS:
                valor, texto = None, text(bruto)
            else:
                valor, texto = num(bruto), (text(bruto) if isinstance(bruto, str) else None)
            if valor is None and texto is None:
                continue
            out.append({"IDMV": r, "IDMP": n, "Value": valor, "ValueText": texto,
                        "ValueClass": classify(n, (r, pcol(n)) in formulas,
                                               bool(v["IsSelecao"]))})
    return out


# --------------------------------------------------------------------------
# BLOCO MV4 -- bloco auxiliar (P52, conjunto MV_AUX)
#   Le      : linhas 165 a 204: as configuracoes que o M2 le. Mesmas colunas
#             da lista de veiculos; a receita de materiais esta em L.
#   Devolve : um valor por configuracao e parametro. A receita entra como o
#             indicador O28 (Material Composition).
# --------------------------------------------------------------------------
def aux_block(g) -> list[dict]:
    out = []
    for r in range(AUX_FIRST, AUX_LAST + 1):
        caso = text(g.get((r, pcol(1))))
        if caso is None:
            continue
        base = {"RefSet": "MV_AUX", "CaseKey": caso, "Workbook": WORKBOOK_NAME, "Sheet": SHEET}
        receita = text(g.get((r, C("L"))))
        if receita:
            out.append({**base, "IDInd": "O28", "ValueText": receita, "Cell": f"L{r}"})
        for n in range(2, N_PARAMS + 1):
            bruto = g.get((r, pcol(n)))
            valor = None if n in TEXT_PARAMS else num(bruto)
            texto = text(bruto) if (n in TEXT_PARAMS or isinstance(bruto, str)) else None
            if valor is None and texto is None:
                continue
            out.append({**base, "IDMP": n, "Value": valor, "ValueText": texto,
                        "Cell": addr(r, pcol(n))})
    return out


# --------------------------------------------------------------------------
# BLOCO MV5 -- gravacao
# --------------------------------------------------------------------------
def main(argv) -> int:
    wb = open_workbook(argv)
    g, formulas = wb.grid(SHEET, formulas=True)
    print("Market Vehicles ->", "data/csv/fase_a")
    write_csv("P54_MarketParam", P54_COLS, market_params(g))
    veiculos = vehicles(g)
    write_csv("P26_MarketVehicle", P26_COLS, veiculos)
    write_csv("P27_MarketVehicleParam", P27_COLS, vehicle_values(g, formulas, veiculos))
    write_csv("P52_ExcelReferenceValue.market_vehicles", P52_COLS, aux_block(g))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
