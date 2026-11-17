"""Receitas de materiais das familias GREET 2022, 2023 e 2024: linhas novas de P15 e P16.

Fase A, complemento do passo 3. A base da 0.9.0 tem duas familias de receitas
(BISD, de consultoria, e PBP_BISD, do Projeto do Berco ao Portao). A rodada
gravada no i3ET de 01/11/2026 usa uma terceira: a composicao das proprias
configuracoes do GREET 2024 (ICEV-G21, HEV-G22, ...). Este script as importa
do bloco de receitas do M2, pelo mesmo caminho que tools/build_base.py usou
para as outras duas.

Blocos:
    RC1  leiaute do bloco: grupos GREET e linhas de material
    RC2  quais colunas sao receitas da familia GREET 2024
    RC3  participacoes por grupo e material, normalizacao e fluidos
    RC4  conferencia: o mesmo metodo reproduz as receitas que a base ja tem
    RC5  gravacao dos CSV

Uso:
    python tools/import_recipes.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import csv
import os
import re
import sys

from fase_a_common import REPO, WORKBOOK_NAME, num, open_workbook, text, write_csv
from xlsx_cells import col2n, n2col

SHEET = "M2 GHG Mfg Module"
C = col2n
ROW_NAME, ROW_RECIPE, ROW_PT = 8, 9, 10          # configuracao, receita que ela usa, motorizacao
FIRST_ROW, LAST_ROW = 82, 281                    # bloco de receitas
COL_IDM, COL_GROUP, COL_MARK = C("L"), C("O"), C("S")
BLOCK_FIRST, BLOCK_LAST = C("T"), C("CA")        # blocos GREET 2022, 2023 e 2024 (linha 7)
ROW_EDITION = 7                                 # 'GREET 2022', 'GREET 2023', 'GREET 2024'
#: A bateria de tracao vem de P20 (por modelo de bateria); os fluidos, das
#: linhas de massa de cada fluido. Nenhum dos dois sai do bloco de receitas.
SKIP_GROUPS = {"Iprinc", "K"}
FLUID_ROWS = {620: "77", 621: "78", 622: "79", 623: "80", 624: "81", 625: "82", 626: "83"}
#: Motorizacao do i3ET -> motorizacao da base. FCV entra no catalogo (FCEV, sem calculo).
POWERTRAIN = {"ICEV": "ICEV", "HEV": "HEV", "PHEV": "PHEV", "BEV": "BEV", "FCV": "FCEV"}
#: Letra da serie -> (carroceria em P13, descricao). A serie G e o carro de
#: passeio, sem distincao entre seda e hatch: fica sem carroceria.
SERIES = {"G": (None, "carro de passeio"), "S": ("SUV", "SUV"), "P": ("PUT", "picape")}
#: Receita da base com a mesma motorizacao, para os fluidos quando a coluna
#: nao traz as massas.
FLUID_FALLBACK = {"ICEV": "BISD2", "HEV": "BISD6", "PHEV": "BISD8", "BEV": "BISD12",
                  "FCEV": "BISD12"}
#: Colunas usadas na conferencia (RC4): receita da base -> nome no i3ET.
CHECK = {"BISD2": "ICEV-BISD2", "BISD6": "HEV-BISD6", "BISD12": "BEV-BISD12",
         "PBP_BISD2": "ICEV-PBP_BISD2", "PBP_BISD8": "PHEV-PBP_BISD8"}

NAME_RE = re.compile(r"^(ICEV|HEV|PHEV|BEV|FCV)-([GSP])(L?\d+)$")
P15_COLS = ["IDVMR", "IDVPT", "IDVDT", "IDVS", "DsVMR"]
P16_COLS = ["IDVMR", "IDGG", "IDM", "MshareGG"]


def _read_csv(nome):
    with open(os.path.join(REPO, "data", "csv", nome), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


# --------------------------------------------------------------------------
# BLOCO RC1 -- leiaute do bloco
#   Le      : colunas L (IDM), O (grupo) e S ('%' abre um grupo), linhas 82-281
#   Devolve : lista de (linha, grupo, IDM)
# --------------------------------------------------------------------------
def layout(g) -> list[tuple[int, str, str]]:
    grupo, linhas = None, []
    for r in range(FIRST_ROW, LAST_ROW + 1):
        if g.get((r, COL_MARK)) == "%":
            grupo = text(g.get((r, COL_GROUP)))
            continue
        idm = text(g.get((r, COL_IDM)))
        if idm is not None and grupo:
            linhas.append((r, grupo, idm))
    return linhas


# --------------------------------------------------------------------------
# BLOCO RC2 -- receitas da familia GREET 2024
#   Le      : linhas 8 a 10 do bloco AR:CA
#   Devolve : {nome: coluna} das colunas que definem a propria receita (o nome
#             da linha 9 e o da linha 8) e cuja motorizacao a base calcula
# --------------------------------------------------------------------------
def greet_recipes(g) -> dict[str, int]:
    out = {}
    for c in range(BLOCK_FIRST, BLOCK_LAST + 1):
        nome = text(g.get((ROW_NAME, c)))
        if nome and nome == text(g.get((ROW_RECIPE, c))) \
                and text(g.get((ROW_PT, c))) in POWERTRAIN \
                and NAME_RE.match(nome):
            out[nome] = c
    return out


def edition_of(g, col) -> str:
    """Edicao do GREET do bloco a que a coluna pertence (rotulo da linha 7)."""
    edicao = None
    for c in range(BLOCK_FIRST, col + 1):
        rotulo = text(g.get((ROW_EDITION, c)))
        if rotulo and rotulo.startswith("GREET "):
            edicao = rotulo
    return edicao


# --------------------------------------------------------------------------
# BLOCO RC3 -- participacoes
#   Le      : a coluna da receita, nas linhas do leiaute e nas dos fluidos
#   Devolve : {(grupo, IDM): participacao}. Linhas repetidas de um material
#             no mesmo grupo sao somadas. Participacao negativa (residuo de
#             fechamento na linha 'Others') entra como zero, como em setembro.
# --------------------------------------------------------------------------
def shares(g, linhas, col, materiais_de_massa) -> tuple[dict, int]:
    vetor, negativos = {}, 0
    for r, grupo, idm in linhas:
        if grupo in SKIP_GROUPS:
            continue
        v = num(g.get((r, col)))
        if v is not None:
            vetor[(grupo, idm)] = vetor.get((grupo, idm), 0.0) + v
    for chave, v in vetor.items():
        if v < 0:
            vetor[chave] = 0.0
            negativos += 1
    # Normalizacao (decisao de 19/09/2026): cada participacao e dividida pela
    # soma, no seu grupo, dos itens de papel 'material' em P09. Os itens de
    # processo trazem um coeficiente de conversao e nao entram na conta.
    soma: dict[str, float] = {}
    for (grupo, idm), v in vetor.items():
        if idm in materiais_de_massa:
            soma[grupo] = soma.get(grupo, 0.0) + v
    for (grupo, idm), v in vetor.items():
        if idm in materiais_de_massa and soma.get(grupo, 0.0) > 0:
            vetor[(grupo, idm)] = v / soma[grupo]
    return vetor, negativos


def fluid_shares(g, col) -> dict | None:
    massas = {idm: (num(g.get((r, col))) or 0.0) for r, idm in FLUID_ROWS.items()}
    total = sum(massas.values())
    return {("K", idm): m / total for idm, m in massas.items()} if total > 0 else None


# --------------------------------------------------------------------------
# BLOCO RC4 -- conferencia do metodo
#   Le      : as colunas BISD e PBP_BISD do i3ET e a P16 da base
#   Devolve : (participacoes comparadas, divergentes)
# --------------------------------------------------------------------------
def mass_materials() -> set[str]:
    """Materiais cujo papel em P09 e 'material' (fracao de massa)."""
    return {r["IDM"] for r in _read_csv("P09.csv") if r["ShareRole"] == "material"}


def check_existing(g, linhas) -> tuple[int, int]:
    coluna = {text(v): c for (r, c), v in g.items() if r == ROW_NAME}
    base = {(r["IDVMR"], r["IDGG"], r["IDM"]): float(r["MshareGG"] or 0)
            for r in _read_csv("P16.csv")}
    comparadas = divergentes = 0
    for vmr, nome in CHECK.items():
        vetor, _ = shares(g, linhas, coluna[nome], mass_materials())
        for (grupo, idm), v in vetor.items():
            if (vmr, grupo, idm) in base:
                comparadas += 1
                divergentes += abs(base[(vmr, grupo, idm)] - v) > 1e-12
    return comparadas, divergentes


# --------------------------------------------------------------------------
# BLOCO RC5 -- montagem e gravacao
# --------------------------------------------------------------------------
def build(g):
    linhas = layout(g)
    materiais = {r["IDM"] for r in _read_csv("P09.csv")}
    de_massa = mass_materials()
    fluidos_base = {}
    for r in _read_csv("P16.csv"):
        if r["IDGG"] == "K":
            fluidos_base.setdefault(r["IDVMR"], {})[("K", r["IDM"])] = float(r["MshareGG"])
    p15, p16, avisos = [], [], []
    for nome, col in greet_recipes(g).items():
        pt = POWERTRAIN[text(g[(ROW_PT, col)])]
        serie, numero = NAME_RE.match(nome).groups()[1:]
        edicao = edition_of(g, col)
        carroceria, classe = SERIES[serie]
        vetor, negativos = shares(g, linhas, col, de_massa)
        fluidos = fluid_shares(g, col)
        if fluidos is None:
            fluidos = fluidos_base[FLUID_FALLBACK[pt]]
            avisos.append(f"{nome}: fluidos da receita {FLUID_FALLBACK[pt]}")
        if negativos:
            avisos.append(f"{nome}: {negativos} participacao(oes) negativa(s) zerada(s)")
        vetor.update(fluidos)
        fora = sorted({idm for (_g, idm) in vetor if idm not in materiais})
        if fora:
            avisos.append(f"{nome}: materiais fora de P09 ignorados: {fora}")
        p15.append({
            "IDVMR": nome, "IDVPT": pt, "IDVDT": carroceria, "IDVS": None,
            "DsVMR": f"Composicao da configuracao {nome} do {edicao} ({classe}, serie "
                     f"{serie}{numero}), extraida da coluna {n2col(col)} do bloco de "
                     f"receitas do i3ET ({WORKBOOK_NAME}, M2, T8:DD281)."})
        p16 += [{"IDVMR": nome, "IDGG": grupo, "IDM": idm, "MshareGG": v}
                for (grupo, idm), v in sorted(vetor.items()) if idm in materiais]
    return p15, p16, avisos


def main(argv) -> int:
    g = open_workbook(argv).grid(SHEET)
    comparadas, divergentes = check_existing(g, layout(g))
    print(f"Conferencia com a base: {comparadas} participacoes comparadas, "
          f"{divergentes} divergentes")
    p15, p16, avisos = build(g)
    for a in avisos:
        print("   aviso:", a)
    print("Receitas GREET 2024 ->", "data/csv/fase_a")
    write_csv("P15_VehicleMaterialRecipe.add", P15_COLS, p15)
    write_csv("P16_MaterialShare.add", P16_COLS, p16)
    return 1 if divergentes else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
