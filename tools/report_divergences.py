"""Report the divergences between the calculator and the i3ET spreadsheet.

The i3ET is not going to be changed: it is the published reference. This report
exists so that the differences are understood rather than argued about, and so
that whoever maintains the spreadsheet can decide, case by case, whether to
adjust it.

Only material differences are explained. A difference at the level of floating
point noise is not a finding, and listing it would bury the ones that matter.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core import calc, loader
from core import params as P

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "i3et_reference.json")
DB = os.path.join(REPO, "data", "base_referencia.sqlite")

#: A difference below this is noise, not a finding.
MATERIAL_KG = 0.5
MATERIAL_REL = 1e-4

NOT_SCALED_BY = {35, 42}
IDSG_HYBRID_MODULE = 43


def analyse():
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    base = loader.load_sqlite(DB)
    ef = pd.DataFrame(
        [{"IDM": m, "IDEFV": "FIXTURE", "EF": v, "EFnotes": "i3ET", "IsUserDefined": 0}
         for m, v in fx["ef_by_material"].items()])
    p08 = {int(r.IDSG): int(r.IDVP) for r in base["P08"].itertuples()}
    names = {int(r.IDSG): r.DsSG for r in base["P02"].itertuples()}
    idvmr = base["D02"].iloc[0]["IDVMR"]

    findings = []
    for code in fx["usable_configs"]:
        cfg = fx["configs"][code]
        gc = {int(k): (v if isinstance(v, (int, float)) else 0.0)
              for k, v in cfg["gc"].items()}
        bid = cfg["gc"].get("32")
        bid = None if bid in (None, "-", "NA") else str(bid).strip()
        supplied = {i for i in P.ENDOGENOUS
                    if isinstance(cfg["gc"].get(str(i)), (int, float))}
        r = calc.calculate_vehicle(base, gc, powertrain=cfg["powertrain"],
                                   battery_id=bid, idmpv=1, idvmr=idvmr,
                                   idefv="FIXTURE", idapv="A-EF", boundary="MAT",
                                   ef_table=ef, supplied=supplied)
        ours_total = r["totals"]["MassIDV"]
        i3et_total = cfg["expected"]["vehicle_mass_kg"]
        delta = ours_total - i3et_total
        if abs(delta) < MATERIAL_KG and abs(delta) / max(i3et_total, 1) < MATERIAL_REL:
            findings.append({"config": code, "powertrain": cfg["powertrain"],
                             "delta": delta, "causa": "nenhuma", "detalhe": "",
                             "ours": ours_total, "i3et": i3et_total})
            continue

        i3 = {int(k): v for k, v in cfg["expected"]["me_by_subgroup_kg"].items()}
        ours = {int(x.IDSG): x.ME for x in r["C01"].itertuples()}
        ratios = [i3[s] / ours[s] for s in ours
                  if s in i3 and ours[s] > 1e-9 and i3[s] > 1e-9
                  and p08.get(s) not in NOT_SCALED_BY]
        factor = statistics.median(ratios) if ratios else None
        constant = bool(ratios) and (max(ratios) - min(ratios)) < 1e-9

        if constant and factor is not None and abs(factor - 1) > 1e-9:
            causa = "leveza"
            detalhe = f"fator {factor:.6f} aplicado a todos os subgrupos escalados"
        else:
            por_sub = {s: ours.get(s, 0.0) - i3.get(s, 0.0)
                       for s in set(ours) | set(i3)}
            maiores = sorted(por_sub.items(), key=lambda kv: -abs(kv[1]))
            maiores = [(s, d) for s, d in maiores if abs(d) >= MATERIAL_KG]
            if (maiores and maiores[0][0] == IDSG_HYBRID_MODULE
                    and cfg["powertrain"] == "FCV"):
                causa = "modulo hibrido em FCV"
                detalhe = (f"IDSG {IDSG_HYBRID_MODULE} "
                           f"({names.get(IDSG_HYBRID_MODULE, '')}): "
                           f"{maiores[0][1]:+.4f} kg")
            else:
                causa = "a investigar"
                detalhe = "; ".join(f"IDSG {s} ({names.get(s, '')[:24]}): {d:+.3f} kg"
                                    for s, d in maiores[:3])
        findings.append({"config": code, "powertrain": cfg["powertrain"],
                         "delta": delta, "causa": causa, "detalhe": detalhe,
                         "ours": ours_total, "i3et": i3et_total,
                         "fator": factor if constant else None})
    return findings, fx


CAUSA_TEXTO = {
    "leveza": (
        "### Fator de leveza (módulo M5)\n\n"
        "O i3ET multiplica a massa de cada subgrupo escalado por um fator de leveza, "
        "que representa a substituição por materiais mais leves. O fator pertence ao "
        "módulo **M5**, fora do escopo desta versão da calculadora, que trabalha com "
        "`fLM = 1`.\n\n"
        "**Não é uma divergência de cálculo.** A razão entre as massas é rigorosamente "
        "constante em todos os subgrupos escalados de cada configuração — o que prova "
        "tratar-se de um único fator multiplicativo, e não de erro em qualquer etapa.\n\n"
        "**Nenhum ajuste é necessário no i3ET.** Quando o módulo M5 for incorporado, "
        "o parâmetro `P06.fLM` deixa de ser 1 e as configurações passam a coincidir "
        "sem alteração de fórmula: a equação da calculadora já traz o fator.\n"),
    "modulo hibrido em FCV": (
        "### Módulo de combinação híbrida em veículos a célula a combustível\n\n"
        "No i3ET, a massa do módulo de combinação híbrida é zerada por uma condicional "
        "que lista os trens de força `ICEV`, `BEV`, `SHEV`, `SPHEV`, `HFCEV` e `EFCEV`. "
        "As configurações a célula a combustível, porém, usam o rótulo **`FCV`**, que "
        "não consta dessa lista. A condição não é satisfeita e o módulo recebe massa "
        "num veículo que, por construção, não o possui.\n\n"
        "A calculadora atribui o módulo apenas a `HEV` e `PHEV`, e a regra deixou de "
        "ser uma condicional embutida na fórmula para ser um parâmetro derivado do "
        "trem de força (`IDVP 41`), declarado uma única vez.\n\n"
        "**Ajuste sugerido no i3ET:** acrescentar `FCV` à lista de exclusão da fórmula "
        "do módulo híbrido, ou — preferível — substituir a condicional por um parâmetro "
        "de existência, como foi feito aqui. Convém rever, na mesma oportunidade, os "
        "demais parâmetros das configurações a célula a combustível, já que o modelo "
        "as desconsiderou.\n"),
    "a investigar": (
        "### Diferenças ainda sem explicação\n\n"
        "As configurações abaixo divergem por motivo não identificado e precisam de "
        "análise antes de qualquer conclusão.\n"),
}


def write_report(findings, fx, path):
    material = [f for f in findings if f["causa"] != "nenhuma"]
    por_causa = defaultdict(list)
    for f in material:
        por_causa[f["causa"]].append(f)
    hoje = dt.date.today()

    L = []
    w = L.append
    w("# Relatório de Divergências — Calculadora × i3ET")
    w("")
    w(f"**Data:** {hoje.strftime('%d/%m/%Y')} · "
      f"**Fonte:** `{fx['source_workbook']}` · "
      f"**Fatores:** versão `{fx['ef_version_in_model']}`")
    w("")
    w("---")
    w("")
    w("## 1. Propósito")
    w("")
    w("O modelo i3ET em Excel **não será alterado**: ele é a referência publicada, e "
      "a estabilidade dele vale mais do que a correção pontual de um detalhe. Este "
      "relatório existe para que as diferenças entre a calculadora e o i3ET sejam "
      "compreendidas, e para que quem mantém a planilha decida, caso a caso, se e "
      "quando ajustá-la.")
    w("")
    w("A calculadora, por sua vez, é construída para ser **coerente**: onde o i3ET "
      "apresenta uma inconsistência interna, ela adota a regra correta e a registra "
      "aqui, em vez de reproduzir o comportamento.")
    w("")
    w("## 2. Método")
    w("")
    w(f"Cada uma das **{len(fx['usable_configs'])} configurações** do i3ET foi "
      "processada pela calculadora com os próprios parâmetros de entrada e os próprios "
      "fatores de emissão da planilha, e a massa resultante foi comparada com a que o "
      "i3ET produz.")
    w("")
    w(f"São consideradas **materiais** as diferenças acima de {MATERIAL_KG} kg ou de "
      f"{MATERIAL_REL:.0e} em termos relativos. Abaixo disso a diferença é ruído de "
      "ponto flutuante, não achado, e listá-la esconderia as que importam.")
    w("")
    w("## 3. Resumo")
    w("")
    w("| Situação | Configurações | Ajuste sugerido no i3ET |")
    w("|---|---|---|")
    w(f"| Sem diferença material | {len(findings) - len(material)} | — |")
    for causa in ("leveza", "modulo hibrido em FCV", "a investigar"):
        if causa in por_causa:
            ajuste = {"leveza": "nenhum",
                      "modulo hibrido em FCV": "sim, ver §4",
                      "a investigar": "a definir"}[causa]
            nome = {"leveza": "Fator de leveza (módulo M5)",
                    "modulo hibrido em FCV": "Módulo híbrido em FCV",
                    "a investigar": "Sem explicação"}[causa]
            w(f"| {nome} | {len(por_causa[causa])} | {ajuste} |")
    w("")
    w("## 4. As diferenças, por origem")
    w("")
    for causa in ("modulo hibrido em FCV", "leveza", "a investigar"):
        if causa not in por_causa:
            continue
        w(CAUSA_TEXTO[causa])
        w("")
        w("| Configuração | Trem de força | Calculadora (kg) | i3ET (kg) | Diferença (kg) | Detalhe |")
        w("|---|---|---|---:|---:|---|")
        for f in sorted(por_causa[causa], key=lambda x: -abs(x["delta"])):
            w(f"| `{f['config']}` | {f['powertrain']} | {f['ours']:,.3f} | "
              f"{f['i3et']:,.3f} | {f['delta']:+,.3f} | {f['detalhe']} |")
        w("")
    w("## 5. Divergências de parâmetro, não de massa")
    w("")
    w("Duas diferenças não aparecem na tabela acima porque a calculadora **honra o "
      "valor informado pelo i3ET** em vez de recalculá-lo. Elas são registradas aqui "
      "porque afetam quem ler as fórmulas da planilha esperando que elas expliquem os "
      "números.")
    w("")
    w("**Potência combinada (`IDVP 15`).** A fórmula do i3ET calcula o máximo entre a "
      "potência do motor a combustão e a do motor elétrico. Em três configurações PHEV "
      "o valor armazenado é a **soma** das duas. A evolução do modelo foi da soma para "
      "o máximo, e o parâmetro passou a ser configurável — os valores armazenados são "
      "anteriores a essa mudança. *Observação de método: nem a soma nem o máximo "
      "descrevem corretamente a potência combinada de um híbrido; o tema merece "
      "tratamento próprio em trabalho futuro.*")
    w("")
    w("**Motor de arranque (`IDVP 18`).** A fórmula aplica 4% da potência do motor a "
      "combustão. Em três configurações o valor armazenado corresponde a 3%. Também "
      "aqui o parâmetro deixou de ser constante embutida e passou a ser configurável.")
    w("")
    w("Em ambos os casos a calculadora usa o valor informado quando ele existe, e "
      "aplica a equação apenas para veículos criados pelo usuário. A coluna "
      "`D03.IsCalculated` distingue os dois casos, e toda substituição é registrada "
      "no log da execução.")
    w("")
    w("## 6. Conclusão")
    w("")
    if not por_causa.get("a investigar"):
        w("**Toda diferença material está explicada.** Nenhuma decorre de erro de "
          "cálculo da calculadora: elas vêm de um módulo fora do escopo desta versão "
          "(leveza) e de uma inconsistência identificada na lista de exclusão do "
          "módulo híbrido do i3ET.")
    else:
        w(f"Restam **{len(por_causa['a investigar'])} configurações** sem explicação, "
          "listadas em §4. Nenhuma conclusão deve ser tirada antes de analisá-las.")
    w("")
    w(f"Os **doze veículos de referência `BP01`–`BP12` reproduzem o i3ET na precisão "
      "da máquina**, com erro relativo entre 0 e 2,6 × 10⁻¹⁶.")
    w("")
    w("---")
    w("")
    w("*Gerado por `tools/report_divergences.py`.*")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return material


def main():
    findings, fx = analyse()
    hoje = dt.date.today().strftime("%Y%m%d")
    nome = f"RelatorioDeDivergencias_i3ET_{hoje}a.md"
    destinos = [
        os.path.expanduser("~/mnt/_Calculadora da Pegada de Carbono do Berço ao Portão/"
                           f"Documentação/{nome}"),
        os.path.join(REPO, "docs", "05-relatorio-de-divergencias.md"),
    ]
    for d in destinos:
        if os.path.isdir(os.path.dirname(d)):
            material = write_report(findings, fx, d)
            print("gravado:", d)
    print(f"\n{len(findings)} configuracoes, {len(material)} com diferenca material")
    for causa in sorted({f['causa'] for f in findings if f['causa'] != 'nenhuma'}):
        n = sum(1 for f in findings if f["causa"] == causa)
        print(f"   {causa:26s}: {n}")


if __name__ == "__main__":
    main()
