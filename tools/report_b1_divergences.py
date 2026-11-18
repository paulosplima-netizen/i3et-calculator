"""Relatorio das divergencias do bloco B1 (docs/05b-divergencias-b1.md).

Mede, com a fixture tests/fixtures/b1_reference.json e a base de referencia, o que o
aplicativo faz de diferente da planilha em tres pontos e quanto isso pesa no GEE:

    B1-DIV-01  calibracao de massa: a planilha (P69 = "Sim") transfere massa de A para B
    B1-DIV-02  T495 antigo em 28 colunas: ignora o seletor e soma T509 duas vezes
    B1-DIV-03  colunas PBP_BISD: pneus e bateria auxiliar proprios

Uso: python tools/report_b1_divergences.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from core import maintenance as mt  # noqa: E402
from core import mass_calibration as mc  # noqa: E402

DB = os.path.join(REPO, "data", "base_referencia.sqlite")
REF = os.path.join(REPO, "tests", "fixtures", "b1_reference.json")
OUT = os.path.join(REPO, "docs", "05b-divergencias-b1.md")


def _idvmr(rec: str) -> str:
    m = re.match(r"^(?:ICEV|HEV|SHEV|PHEV|BEV|FCV)-((?:PBP_)?BISD\d+s?)$", rec)
    return m.group(1) if m else rec


def _ghg_por_kg(c, idvmr: str, idgg: str, ef: dict) -> float:
    return sum(s * ef.get(m, 0.0) for m, s in c.execute(
        "SELECT p.IDM, p.MshareGG FROM P16_MaterialShare p JOIN P09_Material m USING (IDM) "
        "WHERE p.IDVMR=? AND p.IDGG=? AND m.ShareRole='material'", (idvmr, idgg)))


def div01(c, ref, ef):
    linhas = []
    for col, m in ref["mass_calibration"].items():
        d = ref["m2_columns"][col]
        r = d["rows"]
        outros = sum(r[str(i)] for i in range(72, 82))
        t = mc.sheet_method_transfer(m["A_est"], m["B_est"], m["declared_row35"], outros, m["k"])
        rec = _idvmr(d["recipe"])
        ga, gb = _ghg_por_kg(c, rec, "A", ef), _ghg_por_kg(c, rec, "B", ef)
        dg = t * (gb - ga)
        linhas.append((col, d["recipe"], m["k"], t, ga, gb, dg, 100 * dg / r["511"]))
    return linhas


def div02(ref):
    out = []
    for col, d in ref["m2_columns"].items():
        r = d["rows"]
        if "495" not in r or "511" not in r:
            continue
        base = r["496"] + r["499"] + r["501"]
        if abs(r["495"] - base) < 1e-6 or abs(r["495"] - base - r["500"]) < 1e-6:
            continue
        if abs(r["495"] - (base + r["500"] + r["509"])) < 1e-6:
            esperado = base + (r["500"] if d["switch_P495"] == "Sim Bat" else 0.0)
            extra = r["495"] - esperado
            out.append((col, d["recipe"], d["switch_P495"], extra, r["509"], r["500"],
                        100 * extra / r["511"]))
    return out


def div03(c, ref, ef):
    cur = c.execute("SELECT * FROM P31_MaintenanceItem")
    nomes = [x[0] for x in cur.description]
    items = [dict(zip(nomes, r)) for r in cur]
    shares: dict = {}
    for i, m, s in c.execute("SELECT IDMI, IDM, Share FROM P31b_MaintenancePartShare"):
        shares.setdefault(i, {})[m] = s
    out = []
    for col, d in ref["m2_columns"].items():
        if "PBP_" not in d["recipe"]:
            continue
        r = d["rows"]
        rec = _idvmr(d["recipe"])
        sh = dict(c.execute("SELECT IDM, MshareGG FROM P16_MaterialShare WHERE IDVMR=? AND "
                            "IDGG='K' AND IDM IN ('77','78','79','80','81','82','83')", (rec,)))
        fm = {m: float(r["81"]) * s for m, s in sh.items()}
        aux = sum(float(r["78"]) * s * ef.get(m, 0.0) for m, s in c.execute(
            "SELECT IDM, MshareGG FROM P16_MaterialShare WHERE IDVMR=? AND IDGG='Iaux'", (rec,)))
        o = mt.replacements(items, life_km=200000, mode="Sim", part_shares=shares, ef=ef,
                            fluid_mass=fm, group_ghg={"Iaux": aux})["components"]
        dt_ = r["496"] - o["tires"]
        da = r["499"] - o["aux_battery"]
        df = r["501"] - o["fluids"]
        out.append((col, d["recipe"], dt_, da, df, dt_ + da + df, 100 * (dt_ + da + df) / r["511"]))
    return out


def _f(x, n=1):
    return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> int:
    with open(REF, encoding="utf-8") as fh:
        ref = json.load(fh)
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    ef = {m: e for m, e in c.execute(
        "SELECT IDM, EF FROM P11_EmissionFactor WHERE IDEFV='BR23' AND EF IS NOT NULL")}
    d1, d2, d3 = div01(c, ref, ef), div02(ref), div03(c, ref, ef)
    c.close()

    t = ["# Relatório de Divergências — anexo do bloco B1", "",
         f"**Data:** {dt.date.today():%d/%m/%Y} · **Fonte:** `LCA_LV_i3ET_20261101.xlsx` · "
         "Gerado por `tools/report_b1_divergences.py` · Complementa `05-relatorio-de-divergencias.md` "
         "e `05a-divergencias-fase-a.md`", "",
         "O i3ET em Excel não é alterado e prevalece; este anexo mede o que o aplicativo faz de "
         "diferente nas partes que o B1 completa (M1 e M2) e quanto isso pesa no resultado.", "",
         "## B1-DIV-01 — Calibração de massa: o método da planilha move massa de A para B", "",
         "Com `P69 = \"Sim\"` o M2 calcula `A = (declarada − Σ demais grupos)/(1 + k)` e `B = k·A`, "
         "com `k` a razão chassi/carroceria digitada por receita. Isso redistribui a massa entre "
         "carroceria e chassi **mesmo quando a massa declarada é igual à calculada**. O aplicativo "
         "(decisão do autor, 18/11/2026) reparte só a diferença: `A_final = A_est + s·Adj`, "
         "`B_final = B_est + (1 − s)·Adj`, com `s = 1/(1 + k)` por receita (P63); sem diferença, "
         "nada muda. Os fatores de GEE por kg vêm das receitas e da lista BR23.", "",
         "| Coluna | Receita | k | Massa movida de A para B (kg) | GEE/kg de A | GEE/kg de B | "
         "Efeito no GEE (kg CO₂e) | % do T511 |", "|---|---|---|---|---|---|---|---|"]
    for col, rec, k, tr, ga, gb, dg, pc in d1:
        t.append(f"| {col} | {rec} | {_f(k, 4)} | {_f(tr)} | {_f(ga, 2)} | {_f(gb, 2)} | "
                 f"{_f(dg)} | {_f(pc, 2)} |")
    t += ["", "Sinal: o efeito é o que a planilha soma a mais (positivo) ou a menos (negativo) "
          "por mover massa para o chassi, em relação ao aplicativo. Em 6 receitas o chassi pesa "
          "mais que a carroceria nos valores digitados (`k` > 1: FCV-P25, HEV-P27, PHEV-P28, "
          "BEV-P29, FCV-P30, PHEV-S28); conferir a digitação. **Sugestão para o i3ET:** aplicar "
          "só a diferença entre massa declarada e calculada.", "",
          "## B1-DIV-02 — T495 antigo em 28 colunas do M2", "",
          "Em 94 colunas `T495 = I × (T496 + T499 + J × T500 + T501)` segue o seletor `P495`. "
          "Em 28 (GREET 2023, `AF:AO`, e as BISD, `CD:CI`, `CK:CV`) a fórmula é `R495 × (… + T500 + "
          "T509)`: ignora o seletor, inclui sempre a bateria de tração e soma o fim de vida "
          "(`T509`), que `T511` soma de novo. O aplicativo reproduz a forma com seletor. O que a "
          "planilha soma a mais nessas colunas:", "",
          "| Coluna | Receita | Seletor | Excesso em T495 (kg CO₂e) | T509 | T500 | % do T511 |",
          "|---|---|---|---|---|---|---|"]
    for col, rec, sw, ex, t509, t500, pc in d2:
        t.append(f"| {col} | {rec} | {sw} | {_f(ex)} | {_f(t509)} | {_f(t500)} | {_f(pc, 2)} |")
    if d2:
        pcs = [x[6] for x in d2]
        t += ["", f"Entre as {len(d2)} colunas, o excesso vai de {_f(min(pcs), 2)}% a "
              f"{_f(max(pcs), 2)}% do T511 (mediana {_f(statistics.median(pcs), 2)}%). "
              "**Sugestão para o i3ET:** usar a fórmula com seletor nas 28 colunas (o autor "
              "informou que corrigirá).", ""]
    t += ["## B1-DIV-03 — Colunas PBP_BISD", "",
          f"As {len(d3)} colunas do Projeto do Berço ao Portão (`CX:DC` e outras) têm pneus e "
          "bateria auxiliar próprios na "
          "planilha (jogo de pneus e reposição da bateria auxiliar diferentes dos demais). O "
          "aplicativo usa os mesmos itens de reposição (P31) para todas as receitas. Diferença "
          "planilha − aplicativo na vida de 200 mil km:", "",
          "| Coluna | Receita | Pneus | Bateria auxiliar | Fluidos | Total | % do T511 |",
          "|---|---|---|---|---|---|---|"]
    for col, rec, a, b, cc, tot, pc in d3:
        t.append(f"| {col} | {rec} | {_f(a)} | {_f(b)} | {_f(cc, 2)} | {_f(tot)} | {_f(pc, 2)} |")
    t += ["", "**Pendência:** identificar a fórmula própria dessas colunas (autor) antes de decidir "
          "se P31 ganha um cenário PBP.", "",
          "## Efeito por ordem de grandeza",
          "", "- Massa da glider no fim de vida: a linha 662 do M2 soma as massas de material e passa "
          "0,1% da massa por grupo nas receitas com participação negativa zerada (divergência D8, "
          "já registrada): 0,5 a 0,8 kg, ou 0,1 a 0,2 kg CO₂e no fim de vida.", ""]
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(t) + "\n")
    print("gravado:", OUT)
    print("DIV-01 SV1..SV4 %T511:", [round(x[7], 2) for x in d1])
    print("DIV-02:", len(d2), "colunas; excesso % (min, max):",
          (round(min(x[6] for x in d2), 2), round(max(x[6] for x in d2), 2)) if d2 else None)
    print("DIV-03:", len(d3), "colunas; total % (min, max):",
          (round(min(x[6] for x in d3), 2), round(max(x[6] for x in d3), 2)) if d3 else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
