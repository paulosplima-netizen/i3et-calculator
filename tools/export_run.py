"""Exporta uma rodada, ou o projeto inteiro, em JSON (Fase A, passo 6).

Uso:
    python tools/export_run.py projeto.sqlite [--run RUNID] [--saida arquivo.json]

Sem `--run`, exporta o projeto com todas as rodadas. Sem `--saida`, o nome
segue a convencao do projeto (`_AAAAMMDD` e letra do dia).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import run_export  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("projeto")
    ap.add_argument("--run")
    ap.add_argument("--saida")
    args = ap.parse_args(argv)
    conn = sqlite3.connect(f"file:{args.projeto}?mode=ro", uri=True)
    try:
        payload = (run_export.export_run(conn, args.run) if args.run
                   else run_export.export_project(conn))
    finally:
        conn.close()
    problems = run_export.verify(payload)
    if problems:
        print("exportacao recusada: " + "; ".join(problems))
        return 1
    stamp = dt.date.today().strftime("%Y%m%d")
    name = args.saida or f"{'rodada' if args.run else 'projeto'}_{stamp}a.json"
    run_export.write(payload, name)
    print(f"gravado: {name}  ExportHash {payload['ExportHash'][:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
