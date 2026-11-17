"""Apoio comum aos scripts de fixtures da Fase A (passo 3).

Blocos:
    FA1  onde esta a planilha de referencia
    FA2  escrita dos CSV, no mesmo formato de data/csv (';' e UTF-8 com BOM)
    FA3  normalizacao de rotulos da planilha para os da base
"""

from __future__ import annotations

import csv
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(REPO, "data", "csv", "fase_a")
WORKBOOK_NAME = "LCA_LV_i3ET_20261101.xlsx"

# --------------------------------------------------------------------------
# BLOCO FA1 -- planilha de referencia
# --------------------------------------------------------------------------
DEFAULT_SOURCES = [
    os.path.expanduser(f"~/mnt/Model/{WORKBOOK_NAME}"),
    os.path.expanduser("~/OneDrive/Documents/_Unicamp/_Calculadora da Pegada de Carbono/"
                       f"Model/{WORKBOOK_NAME}"),
]


def find_workbook(argv) -> str:
    if len(argv) > 1:
        return argv[1]
    for p in DEFAULT_SOURCES:
        if os.path.exists(p):
            return p
    raise SystemExit("Planilha do i3ET nao encontrada. Passe o caminho como argumento.")


def open_workbook(argv):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from xlsx_cells import Workbook
    return Workbook(find_workbook(argv))


# --------------------------------------------------------------------------
# BLOCO FA2 -- escrita dos CSV
#   Numero inteiro sai sem casa decimal; os demais, com a precisao do Excel.
# --------------------------------------------------------------------------
def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, float):
        return int(v) if v == int(v) and abs(v) < 1e15 else repr(v)
    return v


def write_csv(table: str, header: list[str], rows: list[dict]) -> str:
    os.makedirs(CSV_DIR, exist_ok=True)
    caminho = os.path.join(CSV_DIR, f"{table}.csv")
    with open(caminho, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(header)
        for r in rows:
            w.writerow([_cell(r.get(h)) for h in header])
    print(f"   {table:34s} {len(rows):6d} linhas")
    return caminho


# --------------------------------------------------------------------------
# BLOCO FA3 -- rotulos da planilha -> rotulos da base (P13 e P14)
# --------------------------------------------------------------------------
DESIGN = {"Hatch": "Hatchback", "Sedan": "Sedan", "SUV": "SUV", "PUT": "PUT",
          "Van": "Van", "Chassis": "Chassis"}
SIZE = {"Subcompact": "Subcompact", "Compact": "Compact", "Midsize": "Midsize",
        "Large": "Large", "Extralarge": "ExtraLarge"}


def text(v) -> str | None:
    """Texto da celula, sem espacos nas pontas; vazio e marcadores viram None."""
    if v is None:
        return None
    if isinstance(v, float):
        v = int(v) if v == int(v) else v
    s = str(v).strip()
    return s if s not in ("", ".", "-") else None


def num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
