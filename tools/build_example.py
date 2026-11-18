"""Gera `data/exemplo.sqlite`: o projeto de exemplo, somente leitura (docs/06, T01).

Uma analise EC da categoria A0 (Hatch Compact Regular) com a rodada ja congelada
e calculada. O arquivo e um projeto como qualquer outro, com `IsExample = 1`.

    python tools/build_example.py [--saida data/exemplo.sqlite]

O SQLite nao grava direto em algumas pastas montadas: o script monta o arquivo
numa pasta temporaria e o copia no fim.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import __version__, analysis, project, run  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(REPO, "data", "base_referencia.sqlite")
NAME = "Compact hatch · workbook example"


def build(destino: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "exemplo.sqlite")
        shutil.copyfile(BASE, path)
        conn = sqlite3.connect(path)
        try:
            project.create(conn, NAME)
            idefv = conn.execute("SELECT IDEFV FROM P10_EFVersion WHERE IDEFV = 'BR23'"
                                 ).fetchone()[0]
            apv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion ORDER BY IDAPV "
                               "LIMIT 1").fetchone()[0]
            cfg = dict(fuel="E27", norm="NBR", curve="Default", idefv=idefv, idmpv=1, idapv=apv)
            ida = analysis.create_ec(conn, "Example: Hatch Compact Regular", "A0", cfg)
            workbook = conn.execute("SELECT Value FROM M00_BaseInfo WHERE Key='FaseAWorkbook'"
                                    ).fetchone()
            rid = run.freeze(conn, ida, calculator_version=__version__,
                             reference_workbook=workbook[0] if workbook else "",
                             project_name=NAME)
            run.execute(conn, path, rid)
            conn.execute("UPDATE M03_Project SET IsExample = 1")
            conn.commit()
        finally:
            conn.close()
        shutil.copyfile(path, destino)
    return destino


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--saida", default=os.path.join(REPO, "data", "exemplo.sqlite"))
    args = ap.parse_args()
    print(build(args.saida))


if __name__ == "__main__":
    main()
