"""Carrega as tabelas de dados de mercado do B2 (P48, P47, P60, P70) numa base ja montada.

Mais leve que `load_fase_a.py`: nao refaz as demais tabelas (e por isso nao mexe nas escolhas
gravadas pelo master, como P69). As tabelas do B2 sao editoriais e ficam fora do ParamBaseHash.

Uso:
    python tools/load_b2.py [caminho/para/base.sqlite]
"""

from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import schema  # noqa: E402
from load_fase_a import CSV_DIR_B, DB, _files, _read  # noqa: E402


def main(argv: list[str]) -> int:
    caminho = argv[1] if len(argv) > 1 else DB
    conn = sqlite3.connect(caminho)
    conn.execute("PRAGMA foreign_keys = ON")
    for passo in schema.apply_012(conn):
        print("  ", passo)
    conn.execute("PRAGMA defer_foreign_keys = ON")
    for tabela in reversed(schema.PARAM_TABLES_012):
        conn.execute(f"DELETE FROM {tabela}")
    for tabela in schema.PARAM_TABLES_012:
        n = 0
        for arquivo in _files(tabela, pasta=CSV_DIR_B):
            cab, linhas = _read(arquivo, CSV_DIR_B)
            conn.executemany(f"INSERT INTO {tabela} ({', '.join(cab)}) "
                             f"VALUES ({', '.join('?' * len(cab))})", linhas)
            n += len(linhas)
        print(f"   {tabela:28s} {n:5d}")
    conn.commit()
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    print("foreign_key_check:", len(fk), "violacoes; integrity:",
          conn.execute("PRAGMA integrity_check").fetchone()[0])
    print("ParamBaseHash (inalterado):", conn.execute(
        "SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'").fetchone()[0][:16])
    conn.close()
    return 1 if fk else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
