"""Fixtures do Painel de parametros: revisoes por parametro (P64) e suas fontes (P65).

Painel de parametros e revisao periodica (entre B1 e B2). Le o arquivo de revisao
(JSON extraido do artefato "I3et Parametros Expert", ou o arquivo gerado pela
revisao mensal no mesmo formato), liga cada parametro ao seu IDCP em P30 e grava
os CSV em data/csv/fase_b.

Os valores e as faixas NAO sao copiados: o painel os le de P30. Aqui entram so o
conteudo editorial (recomendacao, justificativa, ressalva, alerta, fontes, aceite).

Blocos:
    PR1  leitura do arquivo de revisao
    PR2  ligacao parametro -> IDCP (nome e secao; excecoes listadas)
    PR3  montagem das linhas de P64 e P65
    PR4  gravacao dos CSV (data/csv/fase_b)

Uso:
    python tools/import_param_review.py [tools/fontes/parametros_expert_20260804.json]
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P30_CSV = os.path.join(REPO, "data", "csv", "fase_a", "P30_ControlParam.csv")
OUT = os.path.join(REPO, "data", "csv", "fase_b")
DEFAULT_SOURCE = os.path.join(REPO, "tools", "fontes", "parametros_expert_20260804.json")

#: Parametros cujo nome no artefato difere do P30 (ou e ambiguo): numero no artefato -> IDCP.
EXCEPTIONS = {14: "X32", 15: "X33", 72: "X94", 78: "X100", 97: "X120"}

COLS_P64 = ["IDRV", "IDCP", "ReviewDate", "Action", "Field", "SuggestedValue",
            "FromValue", "LinkedAlerts", "Rationale", "Caveat", "Alert", "Tag",
            "Spotlight", "Accepted", "AcceptedDate"]
COLS_P65 = ["IDRV", "Seq", "Reference", "Year"]


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%()/.\- ]", "", t)).strip()


# --------------------------------------------------------------------------
# BLOCO PR2 -- ligacao parametro -> IDCP
#   Le      : P30 (IDCP, Section, DsCP)
#   Devolve : {numero do artefato: IDCP}; falha se algum parametro nao for achado.
# --------------------------------------------------------------------------
def link_to_p30(data: list[dict]) -> dict[int, str]:
    with open(P30_CSV, encoding="utf-8-sig", newline="") as fh:
        p30 = list(csv.DictReader(fh, delimiter=";"))
    ids = {r["IDCP"] for r in p30}
    por_nome: dict[str, list[dict]] = {}
    for r in p30:
        por_nome.setdefault(_norm(r["DsCP"]), []).append(r)
    ligacao: dict[int, str] = {}
    for p in data:
        n = p["n"]
        if n in EXCEPTIONS:
            ligacao[n] = EXCEPTIONS[n]
            continue
        cand = por_nome.get(_norm(p["name"]), [])
        cand = [r for r in cand if r["Section"] == p["group"]] or cand
        if len(cand) != 1:
            raise SystemExit(f"parametro {n} ({p['name']}): {len(cand)} candidatos em P30")
        ligacao[n] = cand[0]["IDCP"]
    faltam = [i for i in ligacao.values() if i not in ids]
    if faltam or len(set(ligacao.values())) != len(ligacao):
        raise SystemExit(f"ligacao invalida: {faltam}")
    return ligacao


def _date_us(texto: str) -> str:
    """'Aug 4, 2026' -> '2026-08-04'."""
    meses = {m: i for i, m in enumerate(
        "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
    m = re.match(r"(\w{3})\w* (\d+), (\d{4})", texto)
    return f"{m.group(3)}-{meses[m.group(1)]:02d}-{int(m.group(2)):02d}"


# --------------------------------------------------------------------------
# BLOCO PR3 -- linhas de P64 e P65
# --------------------------------------------------------------------------
def build(origem: dict) -> tuple[list[list], list[list]]:
    data = origem["data"]
    aceites = origem.get("accepted", {})
    ligacao = link_to_p30(data)
    p64, p65 = [], []
    for idrv, p in enumerate(sorted(data, key=lambda x: x["n"]), 1):
        rec = p["rec"]
        ac = aceites.get(str(p["n"]))
        p64.append([
            idrv, ligacao[p["n"]], origem["review_date"], rec["act"], rec.get("field"),
            rec.get("to"), rec.get("from"), rec.get("a"), rec.get("why"), rec.get("cav"),
            " | ".join(p["flags"]) or None, (p["tags"] or [None])[0],
            int(bool(p["spot"])), int(ac is not None),
            _date_us(ac["date"]) if ac else None])
        for seq, s in enumerate(p["sources"], 1):
            ano = s.get("year")
            p65.append([idrv, seq, s["ref"], None if ano in (None, "—", "") else ano])
    return p64, p65


# --------------------------------------------------------------------------
# BLOCO PR4 -- gravacao (';' e UTF-8 com BOM, como os demais CSV)
# --------------------------------------------------------------------------
def _write(nome: str, cols: list[str], linhas: list[list]) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{nome}.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(cols)
        for linha in linhas:
            w.writerow(["" if v is None else v for v in linha])
    print(f"   {nome:28s} {len(linhas):5d} linhas")


def main(argv: list[str]) -> int:
    caminho = argv[1] if len(argv) > 1 else DEFAULT_SOURCE
    with open(caminho, encoding="utf-8") as fh:
        origem = json.load(fh)
    p64, p65 = build(origem)
    _write("P64_ParamRevision", COLS_P64, p64)
    _write("P65_ParamRevisionSource", COLS_P65, p65)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
