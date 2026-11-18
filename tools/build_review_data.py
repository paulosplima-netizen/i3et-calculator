"""Dados dos prototipos de tela (`model-data.js`) a partir da base.

Bloco B0 da Fase B, item 8. Os prototipos HTML do pacote "Interfaces Revisadas
para o i3ET" leem `window.i3etData`, um objeto gravado em `model-data.js`. Aqui as
secoes que vem de tabelas da base sao geradas da base; o resto (estado da tela,
graficos de exemplo, correlacao, custo, uso) nao tem tabela de origem e e copiado
do arquivo que ja existe, sem mudanca. Isso fecha o ciclo: mudou a base, regera-se
o arquivo e os prototipos mostram os mesmos numeros que o aplicativo.

Secoes derivadas:
    panel.params   P30  (205 parametros do Control Panel)
    panel.out      P51  (47 indicadores da tabela de saidas) + valores de P52 (CP_OUT_EC)
    market.params  P54  (58 parametros da Market Vehicles)
    market.vehicles P26 + P27  (154 veiculos: r, flag, cls, oem, model, sales, pt, p;
                   f, pb, ex, grp e key sao copiados do arquivo existente)
    market.pbev    P28 + P55   (843 registros do PBEV/INMETRO)
    market.const.kw_to_hp  P59 (HP_PER_KW)

Blocos:
    RD1  secoes derivadas
    RD2  leitura e gravacao do arquivo
    RD3  conferencia contra o arquivo existente

Uso:
    python tools/build_review_data.py --check ARQUIVO.js
    python tools/build_review_data.py ARQUIVO.js SAIDA.js
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_pbev import FIELDS as PBEV_FIELDS  # noqa: E402
from xlsx_cells import col2n  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
PREFIX = "window.i3etData="


# --------------------------------------------------------------------------
# BLOCO RD1 -- secoes derivadas
# --------------------------------------------------------------------------
def panel_params(conn) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM P30_ControlParam ORDER BY rowid"):
        val = r["DefaultText"] if r["DefaultValue"] is None else r["DefaultValue"]
        out.append({"id": r["IDCP"], "cell": r["Cell"], "sec": r["Section"],
                    "name": r["DsCP"], "unit": r["utCP"], "val": val,
                    "calc": bool(r["IsCalculated"]), "mn": r["MinValue"],
                    "mf": r["MostFrequent"], "mx": r["MaxValue"], "dist": r["Distribution"],
                    "ref": r["Reference"], "lvl": r["Level"]})
    return out


def panel_out(conn) -> list[dict]:
    keys = [r[0] for r in conn.execute(
        "SELECT DISTINCT CaseKey FROM P52_ExcelReferenceValue WHERE RefSet = 'CP_OUT_EC' "
        "ORDER BY CaseKey")]
    out = []
    for r in conn.execute("SELECT * FROM P51_OutputIndicator ORDER BY PanelRow"):
        vals = []
        for k in keys:
            v = conn.execute("SELECT Value, ValueText FROM P52_ExcelReferenceValue "
                             "WHERE RefSet = 'CP_OUT_EC' AND CaseKey = ? AND IDInd = ?",
                             (k, r["IDInd"])).fetchone()
            vals.append(None if v is None else (v[1] if v[0] is None else v[0]))
        if r["IDInd"] == "O9":                 # cabecalho: a propria chave do caso
            vals = list(keys)
        out.append({"r": r["PanelRow"], "label": r["DsInd"], "unit": r["utInd"],
                    "vals": vals, "src": r["SourceModule"], "head": bool(r["IsHeader"])})
    return out


def market_params(conn) -> list[dict]:
    # "Parameter 58" e o nome provisorio da base; o prototipo mostra em branco.
    return [{"n": r["IDMP"], "col": r["SheetColumn"],
             "name": "" if re.fullmatch(r"Parameter \d+", r["DsMP"]) else r["DsMP"],
             "unit": r["utMP"] or "-"}
            for r in conn.execute("SELECT * FROM P54_MarketParam ORDER BY IDMP")]


def market_vehicles(conn) -> list[dict]:
    idmps = [r[0] for r in conn.execute("SELECT IDMP FROM P54_MarketParam ORDER BY IDMP")]
    out = []
    for v in conn.execute("SELECT * FROM P26_MarketVehicle ORDER BY SheetRow"):
        vals = {r[0]: (r[2] if r[1] is None else r[1]) for r in conn.execute(
            "SELECT IDMP, Value, ValueText FROM P27_MarketVehicleParam WHERE IDMV = ?",
            (v["IDMV"],))}
        out.append({"r": v["SheetRow"], "flag": v["NotesMV"], "cls": v["SalesClass"],
                    "oem": v["Brand"], "model": v["Model"], "sales": v["SalesUnits"],
                    "pt": v["IDVPT"], "p": [vals.get(i) for i in idmps]})
    return out


def market_pbev(conn) -> list[list]:
    """[chave, categoria, marca, modelo, versao, ...]: uma coluna por campo da guia.

    Campo que a planilha marca como "nao se aplica" nao esta na base (P55); o
    prototipo o mostra como `\\` (e `-` no selo CONPET).
    """
    out = []
    for r in conn.execute("SELECT * FROM P28_PBEVRecord ORDER BY IDPBR"):
        vals = {x[0]: (x[2] if x[1] is None else x[1]) for x in conn.execute(
            "SELECT FieldName, Value, ValueText FROM P55_PBEVRecordValue WHERE IDPBR = ?",
            (r["IDPBR"],))}
        row = [r["MatchKey"]]
        for col in sorted({*PBEV_FIELDS, "D", "E", "F"}, key=col2n):
            campo = PBEV_FIELDS.get(col)
            if col == "D":
                row.append(r["Brand"])
            elif col == "E":
                row.append(r["Model"])
            elif col == "F":
                row.append(r["Version"])
            else:
                row.append(vals.get(campo, "-" if campo == "SeloCONPET" else "\\"))
        out.append(row)
    return out


def derived(conn) -> dict:
    return {
        ("panel", "params"): panel_params(conn),
        ("panel", "out"): panel_out(conn),
        ("market", "params"): market_params(conn),
        ("market", "vehicles"): market_vehicles(conn),
        ("market", "pbev"): market_pbev(conn),
        ("market", "const", "kw_to_hp"): float(conn.execute(
            "SELECT ValueEC FROM P59_EquationConstant WHERE IDEC = 'HP_PER_KW'").fetchone()[0]),
    }


# --------------------------------------------------------------------------
# BLOCO RD2 -- leitura e gravacao
# --------------------------------------------------------------------------
def read_js(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    return json.loads(txt[txt.index("=") + 1:].strip().rstrip(";"))


def write_js(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PREFIX + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")


def _put(data: dict, path: tuple, value) -> None:
    for k in path[:-1]:
        data = data[k]
    data[path[-1]] = value


def _get(data: dict, path: tuple):
    for k in path:
        data = data[k]
    return data


def build(conn, existing: dict) -> dict:
    data = json.loads(json.dumps(existing))
    for path, value in derived(conn).items():
        if path == ("market", "vehicles"):     # f, pb, ex, grp e key seguem do arquivo
            antigo = {v["r"]: v for v in _get(existing, path)}
            value = [{**antigo.get(v["r"], {}), **v} for v in value]
        if path == ("panel", "params"):        # mantem a ordem do arquivo existente
            ordem = {p["id"]: i for i, p in enumerate(_get(existing, path))}
            value = sorted(value, key=lambda p: ordem.get(p["id"], len(ordem)))
        _put(data, path, value)
    return data


# --------------------------------------------------------------------------
# BLOCO RD3 -- conferencia
#   Devolve, por secao, quantos itens diferem do arquivo existente.
# --------------------------------------------------------------------------
def _empty(x) -> bool:
    return x is None or (isinstance(x, str) and x.strip() in ("", "-", "\\"))


def _close(a, b) -> bool:
    if _empty(a) and _empty(b):
        return True
    if isinstance(a, str) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return _close(b, a)
    if isinstance(b, str) and isinstance(a, (int, float)) and not isinstance(a, bool):
        try:                                # versao "1" na base, 1 no prototipo
            return _close(a, float(b))
        except ValueError:
            return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) <= 1e-5 * max(1.0, abs(a), abs(b))
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return all(_close(a[k], b.get(k)) for k in a)   # so as chaves derivadas
    if isinstance(a, str) and isinstance(b, str):
        return a.replace("\r", "") == b.replace("\r", "")      # fim de linha do Excel
    return a == b


def compare(conn, existing: dict) -> dict[str, tuple[int, int]]:
    out = {}
    for path, value in derived(conn).items():
        old = _get(existing, path)
        name = ".".join(path)
        if path == ("panel", "params"):        # por identificador, nao por posicao
            old_by_id = {p["id"]: p for p in old}
            bad = sum(1 for p in value if not _close(p, old_by_id.get(p["id"])))
            out[name] = (bad + abs(len(value) - len(old)), len(old))
            continue
        if isinstance(value, list):
            n = max(len(value), len(old))
            bad = sum(1 for i in range(n)
                      if i >= len(value) or i >= len(old) or not _close(value[i], old[i]))
            out[name] = (bad, n)
        else:
            out[name] = (0 if _close(value, old) else 1, 1)
    return out


def main(argv) -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    if len(argv) >= 3 and argv[1] == "--check":
        for nome, (bad, n) in compare(conn, read_js(argv[2])).items():
            print(f"{nome:24s} {n - bad:5d} de {n:5d} iguais")
        return 0
    if len(argv) == 3:
        write_js(build(conn, read_js(argv[1])), argv[2])
        print(f"gravado: {argv[2]}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
