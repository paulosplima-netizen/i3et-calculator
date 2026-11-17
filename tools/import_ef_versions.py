"""Versoes de fatores de emissao que a planilha oferece e a base nao tinha.

Fase A, passo 3. A rodada gravada no i3ET usa a lista BR23; a base da 0.9.0
tem G22, G23, G24 e as tres BR25. Este script acrescenta a P10 e a P11 as
sete listas que faltam, lidas da guia 'Emission Factors GREET and BR'.

Blocos:
    EF1  conferencia: G22, G23 e G24 da guia contra a P11 da base
    EF2  versoes novas                    -> P10 (linhas a acrescentar)
    EF3  fatores das versoes novas        -> P11 (linhas a acrescentar)
    EF4  gravacao dos CSV

Uso:
    python tools/import_ef_versions.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import csv
import os
import sys

from fase_a_common import REPO, WORKBOOK_NAME, num, open_workbook, text, write_csv
from xlsx_cells import col2n

SHEET = "Emission Factors GREET and BR"
C = col2n
FIRST_ROW, LAST_ROW = 6, 148
COL_ID = C("AC")
EXISTING = {"AE": "G22", "AF": "G23", "AG": "G24"}
#: Coluna -> (identificador na base, descricao). O '%' de 'BR23_100%' sai do nome.
NEW = {
    "AH": ("GLO23", "Global 2023 - fatores 100% internacionais"),
    "AI": ("BR23", "Brasil 2023 - fatores calculados para ICEV hatch ou seda"),
    "AJ": ("BR23_100", "Brasil 2023 - fatores 100% Brasil"),
    "AK": ("BR23_ICEV_SUV", "Brasil 2023 - fatores calculados para ICEV SUV"),
    "AL": ("BR23_HEV", "Brasil 2023 - fatores calculados para HEV"),
    "AM": ("BR23_PHEV", "Brasil 2023 - fatores calculados para PHEV"),
    "AN": ("BR23_BEV", "Brasil 2023 - fatores calculados para BEV"),
}

#: Confirmado pelo autor do i3ET em 17/11/2026 (participou da elaboracao das listas).
LICENSE_BR23 = ("Publicada com o relatorio Pegada de Carbono do Berco ao Portao e "
                "disponibilizada a AEA e ao governo federal, sem restricao de uso declarada, "
                "com a ressalva de como os fatores foram calculados; usada pelo autor, que "
                "participou da elaboracao, conforme as recomendacoes do relatorio")
P10_COLS = ["IDEFV", "DsEFV", "DateIDEFV", "GWPSet", "SourceEFV", "LicenseEFV"]
P11_COLS = ["IDM", "IDEFV", "EF", "EFnotes"]


def _read_csv(nome):
    with open(os.path.join(REPO, "data", "csv", nome), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def _rows(g):
    """(linha, IDM) das linhas da guia que tem identificador de material."""
    for r in range(FIRST_ROW, LAST_ROW + 1):
        idm = text(g.get((r, COL_ID)))
        if idm is not None:
            yield r, idm


# --------------------------------------------------------------------------
# BLOCO EF1 -- conferencia do metodo
#   Le      : as colunas G22, G23 e G24 da guia e a P11 da base
#   Devolve : o numero de fatores comparados e o de divergentes. Se a leitura
#             reproduz o que a base ja tem, as colunas novas merecem a mesma
#             confianca.
# --------------------------------------------------------------------------
def check_existing(g) -> tuple[int, list[str]]:
    base = {(r["IDM"], r["IDEFV"]): r["EF"] for r in _read_csv("P11.csv")}
    comparados, divergentes = 0, []
    for r, idm in _rows(g):
        for col, efv in EXISTING.items():
            if (idm, efv) not in base:
                continue
            comparados += 1
            lido, gravado = num(g.get((r, C(col)))), base[(idm, efv)]
            igual = (lido is None and gravado == "") or (
                lido is not None and gravado != ""
                and abs(lido - float(gravado)) <= 1e-9 * max(1.0, abs(lido)))
            if not igual:
                divergentes.append(f"IDM {idm} / {efv}: planilha {g.get((r, C(col)))!r}, "
                                   f"base {gravado!r}")
    return comparados, divergentes


# --------------------------------------------------------------------------
# BLOCOS EF2 e EF3 -- versoes e fatores novos
#   Le      : colunas AH:AN, so para os materiais que existem em P09
#   Devolve : (versoes, fatores). 'ND' vira fator ausente (NULL), que nao e
#             zero de emissao.
# --------------------------------------------------------------------------
def new_versions(g) -> tuple[list[dict], list[dict]]:
    materiais = {r["IDM"] for r in _read_csv("P09.csv")}
    versoes, fatores = [], []
    for col, (efv, descricao) in NEW.items():
        versoes.append({
            "IDEFV": efv, "DsEFV": descricao, "DateIDEFV": "2023-12-31",
            "GWPSet": "AR6-100",
            "SourceEFV": f"{WORKBOOK_NAME}, guia '{SHEET}', coluna {col}",
            "LicenseEFV": LICENSE_BR23})
        for r, idm in _rows(g):
            if idm not in materiais:
                continue
            fatores.append({
                "IDM": idm, "IDEFV": efv, "EF": num(g.get((r, C(col)))),
                "EFnotes": f"Valor da guia '{SHEET}' do {WORKBOOK_NAME}, celula {col}{r}."})
    return versoes, fatores


# --------------------------------------------------------------------------
# BLOCO EF4 -- gravacao
# --------------------------------------------------------------------------
def main(argv) -> int:
    g = open_workbook(argv).grid(SHEET)
    comparados, divergentes = check_existing(g)
    print(f"Conferencia G22/G23/G24: {comparados} fatores comparados, "
          f"{len(divergentes)} divergentes")
    for d in divergentes:        # informativo: a base pode ter ajustes deliberados
        print("   ", d)
    versoes, fatores = new_versions(g)
    print("Versoes de fatores ->", "data/csv/fase_a")
    write_csv("P10_EFVersion.add", P10_COLS, versoes)
    write_csv("P11_EmissionFactor.add", P11_COLS, fatores)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
