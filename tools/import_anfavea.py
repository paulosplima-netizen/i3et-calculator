"""Fixtures da ANFAVEA e do total da FENABRAVE: P60 (emplacamento) e P71 (frota estimada).

Uso:  python tools/import_anfavea.py [anuario2025.pdf|.txt] [anuario2026.pdf|.txt]

Aceita o PDF (pdftotext ou pdfplumber) ou o texto ja extraido (`pdftotext -layout`).
Tabelas: 2.3 do Anuario 2025 (1957-2024), 2.2.1 do Anuario 2026 (2016-2025), 1.11 de cada
anuario (frota estimada: 2000-2024 e 2016-2025). Cada edicao revisa os anos anteriores:
guarda-se a edicao de cada numero e `IsAdopted = 1` marca a mais recente (decisao 14).
Total FENABRAVE 2025 (Informativo Ed. 276, pag. 1): usado pelo modelo Excel como total de
mercado; o ranking 50+50 (2.424.281) e a soma de P47, nao um total.
Saida: data/csv/fase_b/P60_FleetLicensingTotal.csv e P71_FleetEstimate.csv.
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import market_data as md  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "csv", "fase_b")
DOC = os.path.expanduser("~/mnt/Documentação/ANFAVEA/") if os.path.isdir(
    os.path.expanduser("~/mnt/Documentação/ANFAVEA/")) else ""
P60_COLS = ["IDFL", "SourceName", "SourceEdition", "RefYear", "VehicleClass", "Units",
            "IsAdopted", "SourceFL", "NotesFL"]
P71_COLS = ["IDFE", "SourceName", "SourceEdition", "RefYear", "VehicleClass", "Units",
            "IsAdopted", "SourceFE", "NotesFE"]
#: Edicoes, da mais antiga para a mais recente (a ultima prevalece).
ED25, ED26 = "Anuario ANFAVEA 2025", "Anuario ANFAVEA 2026"
#: Total FENABRAVE 2025 (Informativo Emplacamentos Ed. 276, pagina 1, linhas A, B e A+B).
FEN_TOTAL = {"Automobiles": 1996531, "LightCommercials": 552931, "LightVehicles": 2549462}


def texto_de(caminho: str) -> str:
    if caminho.lower().endswith(".txt"):
        return open(caminho, encoding="utf-8", errors="replace").read()
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", caminho, "-"], capture_output=True,
                              text=True, check=True).stdout
    return md.read_pdf_text(caminho)


def write_csv(nome: str, cols: list[str], linhas: list[list]) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, nome), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(cols)
        w.writerows(linhas)


def serie(tabelas: list[tuple[str, dict]]) -> list[tuple]:
    """tabelas: [(rotulo da edicao + tabela, {ano: valores})] da mais antiga a mais recente.
    Devolve (rotulo, ano, classe, unidades, adotado)."""
    ultimo: dict[tuple[int, str], str] = {}
    for rotulo, dados in tabelas:
        for ano, v in dados.items():
            for cls in md.ANFAVEA_CLASSES:
                ultimo[(ano, cls)] = rotulo
    out = []
    for rotulo, dados in tabelas:
        for ano in sorted(dados):
            for cls, un in zip(md.ANFAVEA_CLASSES, dados[ano], strict=True):
                out.append((rotulo, ano, cls, un, int(ultimo[(ano, cls)] == rotulo)))
    return out


P72_COLS = ["IDFP", "SourceName", "SourceEdition", "SourceTable", "RefYear", "VehicleClass",
            "Dimension", "Category", "Units", "IsAdopted", "NotesFP"]
NOTAS = {"2.2.8": "Emplacamento por combustivel/tecnologia de propulsao",
         "2.2.9": "Emplacamento de leves eletrificados por tecnologia",
         "2.2.10": "Emplacamento de automoveis por cilindrada (nao inclui eletricos)"}


def main(argv: list[str]) -> int:
    f25 = argv[1] if len(argv) > 1 else DOC + "ANFAVEA_Anuário_2025.pdf"
    f26 = argv[2] if len(argv) > 2 else DOC + "ANFAVEA_Anuário_2026.pdf"
    t25, t26 = texto_de(f25), texto_de(f26)
    lic = serie([(f"{ED25}, tabela 2.3", md.parse_anfavea_table(t25, "2.3 Emplacamento")),
                 (f"{ED26}, tabela 2.2.1", md.parse_anfavea_table(t26, "2.2.1 Emplacamento"))])
    fro = serie([(f"{ED25}, tabela 1.11", md.parse_anfavea_table(t25, "1.11 Estimativa")),
                 (f"{ED26}, tabela 1.11", md.parse_anfavea_table(t26, "1.11 Estimativa"))])
    p60 = []
    for i, (rot, ano, cls, un, ad) in enumerate(lic, 1):
        ed, tab = rot.split(", tabela ")
        p60.append([i, "ANFAVEA", ed, ano, cls, un, ad, f"{ed}, tabela {tab}",
                    "Emplacamento de autoveiculos novos (nacionais e importados)"])
    n = len(p60)
    for k, (cls, un) in enumerate(FEN_TOTAL.items(), 1):
        p60.append([n + k, "FENABRAVE", "FEN2025", 2025, cls, un, 1,
                    "FENABRAVE, Informativo Emplacamentos Ed. 276 (2025_12_02.pdf), pag. 1",
                    "Total do mercado; usado em Reference Vehicles!P20:R20 do modelo Excel"])
    p71 = []
    for i, (rot, ano, cls, un, ad) in enumerate(fro, 1):
        ed, tab = rot.split(", tabela ")
        p71.append([i, "ANFAVEA", ed, ano, cls, un, ad, f"{ed}, tabela {tab}",
                    "Estimativa da frota de autoveiculos; a edicao nova revisa os anos anteriores"])
    p72 = []
    for tab in ("2.2.8", "2.2.9", "2.2.10"):
        for ano, cls, dim, cat, un in md.parse_anfavea_columns(t26, tab):
            p72.append([len(p72) + 1, "ANFAVEA", ED26, tab, ano, cls, dim, cat, un, 1,
                        NOTAS[tab]])
    write_csv("P72_FleetLicensingByPowertrain.csv", P72_COLS, p72)
    write_csv("P60_FleetLicensingTotal.csv", P60_COLS, p60)
    write_csv("P71_FleetEstimate.csv", P71_COLS, p71)
    print(f"P60 {len(p60)} linhas | P71 {len(p71)} linhas | P72 {len(p72)} linhas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
