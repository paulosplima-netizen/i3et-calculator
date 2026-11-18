"""Carrega as fixtures da Fase A em data/base_referencia.sqlite.

Fase A, passo 3. E a unica ponte entre data/csv/fase_a e a base: roda depois
de tools/make_db.py (que monta P01 a P25) e pode ser repetida.

Blocos:
    LD1  migracao da base para o esquema 0.10
    LD2  linhas a acrescentar ou atualizar em tabelas da 0.9.0 (arquivos .add)
    LD3  tabelas novas, recarregadas por inteiro
    LD4  entradas das tabelas novas no dicionario em dados (P01)
    LD5  verificacao e impressao digital

Uso:
    python tools/load_fase_a.py [caminho/para/base.sqlite]
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import schema  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
CSV_DIR = os.path.join(REPO, "data", "csv", "fase_a")
CSV_DIR_B = os.path.join(REPO, "data", "csv", "fase_b")
DICIONARIO = os.path.join(REPO, "docs", "07-dicionario-de-dados-fase-a.md")
WORKBOOK = "LCA_LV_i3ET_20261101.xlsx"

#: Tabelas da 0.9.0 que recebem linhas, em ordem de dependencia.
ADDITIONS = ["P10_EFVersion", "P11_EmissionFactor", "P12_Powertrain", "P13_DesignType",
             "P15_VehicleMaterialRecipe", "P16_MaterialShare",
             "P18_BatteryTechnology", "P19_BatteryModel", "P20_BatteryMaterialShare"]


def _read(arquivo: str, pasta: str = CSV_DIR) -> tuple[list[str], list[list]]:
    """Cabecalho e linhas de um CSV; celula vazia e NULL."""
    with open(os.path.join(pasta, arquivo), encoding="utf-8-sig", newline="") as fh:
        linhas = list(csv.reader(fh, delimiter=";"))
    return linhas[0], [[None if c == "" else c for c in linha] for linha in linhas[1:]]


def _files(tabela: str, sufixo: str = "", pasta: str = CSV_DIR) -> list[str]:
    """Arquivos de uma tabela: 'Tabela.csv' e 'Tabela.<parte>.csv'."""
    padrao = re.compile(rf"^{tabela}(\.[a-z_]+)?{re.escape(sufixo)}\.csv$")
    return sorted(f for f in os.listdir(pasta)
                  if padrao.match(f) and (sufixo or not f.endswith(".add.csv")))


def _pk(conn, tabela: str) -> list[str]:
    return [r[1] for r in sorted(conn.execute(f"PRAGMA table_info({tabela})"),
                                 key=lambda r: r[5]) if r[5] > 0]


# --------------------------------------------------------------------------
# BLOCO LD2 -- acrescimos a tabelas da 0.9.0
#   Le      : os arquivos '<Tabela>.add.csv'
#   Faz     : insere a linha nova; se a chave ja existe, atualiza as colunas
#             do arquivo. Nenhuma linha e apagada.
# --------------------------------------------------------------------------
def load_additions(conn) -> dict[str, int]:
    feito = {}
    for tabela in ADDITIONS:
        for arquivo in _files(tabela, ".add"):
            header, linhas = _read(arquivo)
            chave = _pk(conn, tabela)
            demais = [c for c in header if c not in chave]
            sql = (f"INSERT INTO {tabela} ({', '.join(header)}) "
                   f"VALUES ({', '.join('?' * len(header))}) "
                   f"ON CONFLICT ({', '.join(chave)}) DO UPDATE SET "
                   + ", ".join(f"{c} = excluded.{c}" for c in demais))
            conn.executemany(sql, linhas)
            feito[tabela] = feito.get(tabela, 0) + len(linhas)
    return feito


# --------------------------------------------------------------------------
# BLOCO LD3 -- tabelas novas
#   Le      : os arquivos '<Tabela>.csv' e '<Tabela>.<parte>.csv'
#   Faz     : esvazia as tabelas (filhas primeiro) e recarrega (pais primeiro)
# --------------------------------------------------------------------------
def load_new_tables(conn) -> dict[str, int]:
    """Tabelas da 0.10 (CSV em fase_a) e do B1 (0.11; CSV em fase_b)."""
    for tabela in reversed(schema.PARAM_TABLES_010 + schema.PARAM_TABLES_011):
        conn.execute(f"DELETE FROM {tabela}")
    feito = {}
    for tabela, pasta in ([(t, CSV_DIR) for t in schema.PARAM_TABLES_010]
                          + [(t, CSV_DIR_B) for t in schema.PARAM_TABLES_011]):
        feito[tabela] = 0
        if not os.path.isdir(pasta):
            continue
        for arquivo in _files(tabela, pasta=pasta):
            header, linhas = _read(arquivo, pasta)
            conn.executemany(
                f"INSERT INTO {tabela} ({', '.join(header)}) "
                f"VALUES ({', '.join('?' * len(header))})", linhas)
            feito[tabela] += len(linhas)
    return feito


# --------------------------------------------------------------------------
# BLOCO LD4 -- dicionario em dados (P01)
#   Le      : as colunas do banco e as descricoes de docs/07
#   Faz     : regrava as entradas das tabelas da 0.10 em P01_DataDictionary
# --------------------------------------------------------------------------
def load_dictionary(conn) -> int:
    with open(DICIONARIO, encoding="utf-8") as fh:
        texto = fh.read()
    n = 0
    for tabela in schema.TABLES_010:
        curto = tabela.split("_")[0]
        secao = re.search(rf"^### .*`{tabela}` \((.*?)\)\n(.*?)(?=^### |^## |\Z)",
                          texto, re.S | re.M)
        titulo, corpo = secao.group(1), secao.group(2)
        descricao = {m.group(1): m.group(2).strip() for m in re.finditer(
            r"^\| `(\w+)` \|.*\| (.*?) \|$", corpo, re.M)}
        fks = {r[3]: f"{r[2].split('_')[0]}.{r[4]}"
               for r in conn.execute(f"PRAGMA foreign_key_list({tabela})")}
        conn.execute("DELETE FROM P01_DataDictionary WHERE IDTable = ?", (curto,))
        for cid, nome, tipo, notnull, _padrao, pk in conn.execute(
                f"PRAGMA table_info({tabela})"):
            papel = "PK" if pk else ("FK" if nome in fks else "-")
            classe = "Idx" if (pk or nome in fks) else (
                "Exo" if tipo in ("REAL", "INTEGER") else "Dsc")
            conn.execute(
                "INSERT INTO P01_DataDictionary (IDTable, ColumnName, ColumnOrder, SQLType, "
                "KeyRole, FKTarget, ParamClass, Required, DsColumnName, TableName) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (curto, nome, cid + 1, tipo, papel, fks.get(nome), classe,
                 int(bool(notnull or pk)), descricao.get(nome), titulo))
            n += 1
    return n


# --------------------------------------------------------------------------
# BLOCOS LD1 e LD5 -- migracao, verificacao e impressao digital
# --------------------------------------------------------------------------
def reset_010(conn) -> list[str]:
    """Recria as tabelas da 0.10 cuja definicao mudou depois de gravadas.

    As tabelas de parametros sao recarregadas por inteiro a cada execucao; as
    do usuario so podem ser descartadas se estiverem vazias (e numa base de
    referencia estao). Assim uma mudanca de esquema da 0.10, ainda nao
    publicada, chega a base sem refazer P01 a P25.
    """
    presentes = schema.table_names(conn)
    for tabela in schema.ANALYSIS_TABLES:
        if tabela in presentes and conn.execute(
                f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]:
            raise SystemExit(f"{tabela} tem linhas: esta nao e uma base de referencia")
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DROP VIEW IF EXISTS R46_RunComparison")
    b1 = [t for t in reversed(schema.TABLES_011) if t in presentes]
    for tabela in b1:
        conn.execute(f"DROP TABLE {tabela}")
    soltas = [t for t in reversed(schema.ANALYSIS_TABLES + schema.PARAM_TABLES_010)
              if t in presentes]
    for tabela in soltas:
        conn.execute(f"DROP TABLE {tabela}")
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    return soltas


def main(argv) -> int:
    caminho = argv[1] if len(argv) > 1 else DB
    conn = sqlite3.connect(caminho)
    conn.execute("PRAGMA foreign_keys = ON")
    reset_010(conn)
    for passo in schema.migrate(conn):                       # LD1
        print("  ", passo)

    conn.execute("BEGIN")
    # P26 aponta para si mesma (o SELECAO vem antes do seu representativo):
    # a verificacao das chaves fica para o commit.
    conn.execute("PRAGMA defer_foreign_keys = ON")
    acrescimos = load_additions(conn)
    novas = load_new_tables(conn)
    n_dic = load_dictionary(conn)
    conn.commit()

    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    integridade = conn.execute("PRAGMA integrity_check").fetchone()[0]
    base_hash = schema.param_base_hash(conn)
    conn.executemany("INSERT OR REPLACE INTO M00_BaseInfo VALUES (?,?)", [
        ("ParamBaseHash", base_hash),
        ("FaseAWorkbook", WORKBOOK),
        ("FaseABuiltAt", dt.datetime.now().isoformat(timespec="seconds")),
        ("SchemaVersion", schema.SCHEMA_VERSION),
    ])
    conn.commit()
    conn.close()

    print("\nAcrescimos a tabelas da 0.9.0")
    for t, n in acrescimos.items():
        print(f"   {t:32s} {n:6d}")
    print("Tabelas novas")
    for t, n in novas.items():
        print(f"   {t:32s} {n:6d}")
    print(f"Dicionario em dados (P01): {n_dic} colunas")
    print(f"\nintegrity_check: {integridade}")
    print(f"foreign_key_check: {len(fk)} violacoes")
    for v in fk[:15]:
        print("   ", v)
    print(f"ParamBaseHash: {base_hash[:16]}...")
    print("gravado:", caminho)
    return 1 if (fk or integridade != "ok") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
