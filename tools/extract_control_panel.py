"""Fixtures do Control Panel: P29, P30, P51 e a parte de saidas de P52.

Fase A, passo 3. Le a guia 'i3ET Control Panel' (e a 'Market Vehicles', para
localizar os veiculos SELECAO) e grava os CSV em data/csv/fase_a.

Blocos:
    CP1  catalogo de parametros            -> P30
    CP2  categorias A0 a A5                -> P29
    CP3  indicadores e valores de saida    -> P51 e P52 (CP_OUT_EC, CP_OUT_FC)
    CP4  gravacao dos CSV

Uso:
    python tools/extract_control_panel.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import re
import sys

from fase_a_common import DESIGN, SIZE, WORKBOOK_NAME, num, open_workbook, text, write_csv
from xlsx_cells import addr, col2n

SHEET = "i3ET Control Panel"
C = col2n

# Secao do painel -> modulo que consome os parametros. Atribuicao por secao,
# a refinar quando o nucleo de cada modulo passar a ler os parametros.
SECTION_MODULE = {"UPP": "M4", "PET": "M3", "LMP": "M4", "FEF": "M4",
                  "MEF": "M1M2", "AUC": "M6", "LWP": "M5"}
#: Escolhas da analise que o painel lista entre os parametros (ficam em D06).
CHOICES = {"X19", "X27", "X31"}
#: Bloco Basic (AW:AY): celula do valor -> parametro a que corresponde.
BASIC_CELLS = {"AY18": "X23", "AY19": "X24", "AY20": "F20", "AY21": "F25",
               "AY24": "X35", "AY25": "X66", "AY26": "X83", "AY28": "X79", "AY29": "X80"}
#: Trecho do rotulo do indicador -> combustivel a que a linha se refere.
FUEL_IN_LABEL = [("ethanol E100", "Ethanol E100"), ("gasoline E30", "Gasoline E30"),
                 ("gasoline A", "Gasoline A"), ("diesel B15", "Diesel B15"),
                 ("gas VMB B0", "Gas VMB B0")]

P30_COLS = ["IDCP", "Cell", "Section", "Level", "DsCP", "utCP", "IsCalculated",
            "DefaultValue", "DefaultText", "BasicValue", "BasicCell", "MinValue",
            "MostFrequent", "MaxValue", "Distribution", "StdDev", "Reference", "UsedByModule"]
P29_COLS = ["IDVC", "DsVC", "CaseDigit", "IDVDT", "IDVS", "IDLR", "MarketGroup",
            "IDMVSelecao", "IDMVRepresentative"]
P51_COLS = ["IDInd", "DsInd", "utInd", "SourceModule", "PanelRow", "IsHeader",
            "ValueKind", "FuelScenario", "CalcStatus"]
P52_COLS = ["RefSet", "CaseKey", "IDInd", "IDMP", "Value", "ValueText",
            "Workbook", "Sheet", "Cell"]


# --------------------------------------------------------------------------
# BLOCO CP1 -- catalogo de parametros (P30)
#   Le      : bloco Expert (X:AD, linhas 19 a 144), bloco Expanded (F:Q,
#             linhas 17 a 219) e bloco Basic (AW:AY)
#   Devolve : uma linha por parametro
#   Regras  : no Expert, e parametro a linha que tem numero de ordem em W; o
#             numero liga a linha a do Expanded (coluna D), de onde vem a
#             distribuicao, o desvio padrao e a referencia. No Expanded, so
#             entram as linhas marcadas '~' em D, que nao existem no Expert.
# --------------------------------------------------------------------------
def control_params(g, formulas) -> list[dict]:
    def is_header(v):
        return isinstance(v, str) and re.match(r"^[A-Z]{3} - ", v)

    expanded_by_order, expanded_only, secao = {}, [], None
    for r in range(8, 220):
        f, d = g.get((r, C("F"))), g.get((r, C("D")))
        if is_header(f):                 # o titulo da secao traz a sigla em D
            secao = f[:3]
            continue
        if d is None:
            continue
        linha = {"row": r, "sec": secao, "name": text(f), "unit": text(g.get((r, C("G")))),
                 "dist": text(g.get((r, C("H")))), "mn": num(g.get((r, C("I")))),
                 "mf": num(g.get((r, C("J")))), "mx": num(g.get((r, C("K")))),
                 "ref": text(g.get((r, C("O")))), "val": g.get((r, C("P"))),
                 "sd": num(g.get((r, C("Q"))))}
        if d == "~":
            expanded_only.append(linha)
        elif isinstance(d, float):
            expanded_by_order.setdefault(d, linha)

    out, secao = [], None
    for r in range(18, 145):
        x, w = g.get((r, C("X"))), g.get((r, C("W")))
        if is_header(x):
            secao = x[:3]
            continue
        if w is None:
            continue
        idcp, z = f"X{r}", g.get((r, C("Z")))
        e = expanded_by_order.get(w, {})
        out.append({
            "IDCP": idcp, "Cell": f"Z{r}", "Section": secao,
            "Level": "B" if g.get((r, C("AD"))) == "B" else "E",
            "DsCP": text(x), "utCP": text(g.get((r, C("Y")))),
            "IsCalculated": int((r, C("Z")) in formulas),
            "DefaultValue": num(z), "DefaultText": text(z) if isinstance(z, str) else None,
            "MinValue": num(g.get((r, C("AA")))), "MostFrequent": num(g.get((r, C("AB")))),
            "MaxValue": num(g.get((r, C("AC")))),
            "Distribution": e.get("dist"),
            "StdDev": e.get("sd") if e.get("dist") else None,
            "Reference": e.get("ref"),
            "UsedByModule": "UI" if idcp in CHOICES else SECTION_MODULE.get(secao)})
    for e in expanded_only:
        r, v = e["row"], e["val"]
        out.append({
            "IDCP": f"F{r}", "Cell": f"P{r}", "Section": e["sec"], "Level": "X",
            "DsCP": e["name"], "utCP": e["unit"],
            "IsCalculated": int((r, C("P")) in formulas),
            "DefaultValue": num(v), "DefaultText": text(v) if isinstance(v, str) else None,
            "MinValue": e["mn"], "MostFrequent": e["mf"], "MaxValue": e["mx"],
            "Distribution": e["dist"], "StdDev": e["sd"] if e["dist"] else None,
            "Reference": e["ref"], "UsedByModule": SECTION_MODULE.get(e["sec"])})

    por_id = {p["IDCP"]: p for p in out}
    for cell, idcp in BASIC_CELLS.items():
        r = int(cell[2:])
        por_id[idcp]["BasicValue"] = num(g.get((r, C("AY"))))
        por_id[idcp]["BasicCell"] = cell
    return out


# --------------------------------------------------------------------------
# BLOCO CP2 -- categorias (P29)
#   Le      : X12:Z17 (codigo, nome, SELECAO) e AM7:AR8 (SELECAO e veiculo
#             representativo); na Market Vehicles, a linha de cada veiculo
#   Devolve : uma linha por categoria. IDMV e a linha do veiculo na planilha.
# --------------------------------------------------------------------------
def categories(g, mv) -> list[dict]:
    linha_de = {text(mv.get((r, C("N")))): r for r in range(7, 162)}
    representativo = {text(g.get((7, c))): text(g.get((8, c)))
                      for c in range(C("AM"), C("AR") + 1)}
    out = []
    for r in range(12, 18):
        codigo, selecao = text(g[(r, C("X"))]), text(g[(r, C("Z"))])
        lv = linha_de[selecao]
        out.append({
            "IDVC": codigo, "DsVC": text(g[(r, C("Y"))]), "CaseDigit": int(codigo[1:]),
            "IDVDT": DESIGN[text(mv[(lv, C("BC"))])], "IDVS": SIZE[text(mv[(lv, C("BE"))])],
            "IDLR": text(mv[(lv, C("BD"))]), "MarketGroup": text(mv.get((lv, C("DF")))),
            "IDMVSelecao": lv, "IDMVRepresentative": linha_de[representativo[selecao]]})
    return out


# --------------------------------------------------------------------------
# BLOCO CP3 -- indicadores (P51) e valores gravados (P52)
#   Le      : tabela de saidas BN9:BV55 (rodada equalizada) e o bloco de livre
#             escolha BD9:BI55
#   Devolve : (indicadores, valores). So entram no conjunto CP_OUT_FC as
#             linhas em que o bloco de livre escolha traz o mesmo indicador
#             que a tabela de saidas.
# --------------------------------------------------------------------------
def outputs(g) -> tuple[list[dict], list[dict]]:
    ind, ref = [], []
    casos_ec = [text(g[(9, c)]) for c in range(C("BP"), C("BU") + 1)]
    casos_fc = [text(g[(9, c)]) for c in range(C("BF"), C("BI") + 1)]
    for r in range(9, 56):
        rotulo = text(g.get((r, C("BN"))))
        if rotulo is None:
            continue
        vals = [g.get((r, c)) for c in range(C("BP"), C("BU") + 1)]
        cabecalho = all(v is None for v in vals)
        textual = any(isinstance(v, str) for v in vals)
        modulo = text(g.get((r, C("BV"))))
        idind = f"O{r}"
        ind.append({
            "IDInd": idind, "DsInd": rotulo, "utInd": text(g.get((r, C("BO")))),
            "SourceModule": modulo, "PanelRow": r, "IsHeader": int(cabecalho),
            "ValueKind": "Text" if textual else "Num",
            "FuelScenario": next((f for t, f in FUEL_IN_LABEL if t in rotulo), None),
            "CalcStatus": "Calculated" if modulo == "M2 GHG Mfg Module" else "ExcelReference"})
        if cabecalho:
            continue
        blocos = [("CP_OUT_EC", casos_ec, C("BP"))]
        if text(g.get((r, C("BD")))) == rotulo:
            blocos.append(("CP_OUT_FC", casos_fc, C("BF")))
        for conjunto, casos, c0 in blocos:
            for i, caso in enumerate(casos):
                v = g.get((r, c0 + i))
                if v is None or caso == v:
                    continue
                ref.append({"RefSet": conjunto, "CaseKey": caso, "IDInd": idind,
                            "Value": num(v), "ValueText": v if isinstance(v, str) else None,
                            "Workbook": WORKBOOK_NAME, "Sheet": SHEET, "Cell": addr(r, c0 + i)})
    return ind, ref


# --------------------------------------------------------------------------
# BLOCO CP4 -- gravacao
# --------------------------------------------------------------------------
def main(argv) -> int:
    wb = open_workbook(argv)
    g, formulas = wb.grid(SHEET, formulas=True)
    mv = wb.grid("Market Vehicles")
    print("Control Panel ->", "data/csv/fase_a")
    write_csv("P30_ControlParam", P30_COLS, control_params(g, formulas))
    write_csv("P29_VehicleCategory", P29_COLS, categories(g, mv))
    ind, ref = outputs(g)
    write_csv("P51_OutputIndicator", P51_COLS, ind)
    write_csv("P52_ExcelReferenceValue.control_panel", P52_COLS, ref)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
