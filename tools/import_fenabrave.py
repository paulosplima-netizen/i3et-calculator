"""Fixtures dos dados de mercado do B2: P48, P47, P60 e P70.

B2. Le a planilha (guia 'Most Licensed 2025' e o bloco de segmentos da 'Market Vehicles') e,
se o informativo da FENABRAVE for dado como texto, grava nele as unidades de origem
(`UnitsSource`); sem o informativo, `UnitsSource` = `UnitsAdopted` e a nota diz isso.

Blocos:
    FB1  edicao (P48)
    FB2  licenciamentos por modelo (P47), ligados ao catalogo (P26)
    FB3  (P60 e P71 vem de tools/import_anfavea.py)
    FB4  segmentos de referencia (P70)
    FB5  gravacao dos CSV (data/csv/fase_b)

Uso:
    python tools/import_fenabrave.py [planilha.xlsx] [informativo.txt]
"""

from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import market_data as md  # noqa: E402
from xlsx_cells import Workbook, col2n  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "csv", "fase_b")
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
DEFAULT_BOOK = os.path.expanduser("~/mnt/Model/LCA_LV_i3ET_20261119.xlsx")
IDMSE = "FEN2025"
CLASSES = {"AUTOMÓVEIS": "V", "COMERCIAIS LEVES": "CL"}
#: Linhas 207 a 223 da Market Vehicles -> categoria cuja SELECAO as usa (Control Panel,
#: Market Vehicles N228:CZ233). Linhas fora do mapa so entram na cobertura.
SEGMENT_CATEGORY = {207: "A0", 208: "A0", 209: "A1", 210: "A2", 211: "A2", 212: "A2",
                    213: "A3", 214: "A3", 215: "A4", 219: "A5", 220: "A5", 221: "A5"}
LABELS = {"Hatch": "Hatchback", "SubCompact": "Subcompact"}
P48_COLS = ["IDMSE", "SourceName", "PeriodKind", "PeriodStart", "PeriodEnd", "EditionRef",
            "SourceMSE", "PublishedAt", "ImportedAt", "RecordCount", "IsAdopted", "NotesMSE",
            "BulletinUnitsV", "BulletinUnitsCL"]
P47_COLS = ["IDMS", "IDMSE", "SalesClass", "Ranking", "Brand", "Model", "MatchKey",
            "UnitsSource", "UnitsAdopted", "IDMV", "AdjustmentNote", "SheetRow",
            "UnitsReported", "UnitsPrevious", "UnitsPBEV", "SplitMethod", "SplitBasis"]
P70_COLS = ["IDRS", "IDVC", "IDVDT", "IDVS", "FuelGroup", "IDVPT", "SheetRow", "NotesRS"]


def write_csv(nome: str, cols: list[str], linhas: list[list]) -> None:
    import csv
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, nome), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(cols)
        for r in linhas:
            w.writerow(["" if v is None else v for v in r])


def main(argv: list[str]) -> int:
    livro = argv[1] if len(argv) > 1 else DEFAULT_BOOK
    wb = Workbook(livro)
    g = wb.grid("Most Licensed 2025")
    mv = wb.grid("Market Vehicles")
    conn = sqlite3.connect(DB)
    catalogo = {md.match_key(b, m): i for i, b, m in conn.execute(
        "SELECT IDMV, Brand, Model FROM P26_MarketVehicle WHERE IsSelecao = 0")}

    origem: dict[str, int] = {}
    semitotais = [None, None]            # soma das linhas do informativo: V e CL
    if len(argv) > 2:
        secao = md.adopted_section(md.parse_fenabrave_text(open(argv[2], encoding="utf-8").read()))
        origem = {r.key: r.units for r in secao.rows} if secao else {}
        if secao:
            semitotais = [sum(r.units for r in secao.rows if r.sales_class == c)
                          for c in ("V", "CL")]

    # FB2 -- P47
    p47, n = [], 0
    for lin in range(3, 125):
        cat = g.get((lin, 2))
        if cat not in CLASSES:
            continue
        marca, modelo, un = g.get((lin, 4)), g.get((lin, 6)), g.get((lin, 14))
        if not marca or modelo is None or un is None:
            continue
        n += 1
        chave = md.match_key(marca, modelo)
        adotado = int(un)
        fonte = origem.get(chave)
        nota = None
        if not origem:
            fonte, nota = adotado, "sem informativo: origem = adotado"
        elif fonte is None:
            fonte, nota = adotado, "modelo nao encontrado no informativo (ajuste do autor)"
        elif fonte != adotado:
            nota = "unidades redistribuidas pelo autor entre motorizacoes (Powertrain breakdown)"
        p47.append([n, IDMSE, CLASSES[cat], int(g.get((lin, 3)) or 0) or None, marca, modelo,
                    chave, fonte, adotado, catalogo.get(chave), nota, lin,
                    None if nota else fonte, None, None, "Workbook" if nota else "Reported",
                    nota])
    p48 = [[IDMSE, "FENABRAVE", "YTD", "2025-01", "2025-12", "Ed. 276",
            "LCA_LV_i3ET_20261119.xlsx, guia 'Most Licensed 2025'"
            + ("; informativo Ed. 276" if origem else ""), "2026-01", None, len(p47), 1,
            "Acumulado de 2025; UnitsAdopted e o valor usado pelo modelo", *semitotais]]
    write_csv("P48_MarketSalesEdition.csv", P48_COLS, p48)
    write_csv("P47_MarketSales.csv", P47_COLS, p47)

    # FB3 -- P60 e P71 (ANFAVEA, total FENABRAVE): tools/import_anfavea.py

    # FB4 -- P70
    p70 = []
    for lin in range(207, 224):
        dt_, sz = mv.get((lin, col2n("BC"))), mv.get((lin, col2n("BE")))
        p70.append([lin - 206, SEGMENT_CATEGORY.get(lin), LABELS.get(dt_, dt_),
                    LABELS.get(sz, sz), mv.get((lin, 1)), mv.get((lin, 13)), lin, None])
    write_csv("P70_ReferenceSegment.csv", P70_COLS, p70)
    print(f"P48 1 | P47 {len(p47)} (ligados ao catalogo: "
          f"{sum(1 for r in p47 if r[9])}) | P70 {len(p70)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
