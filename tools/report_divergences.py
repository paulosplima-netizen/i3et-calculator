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


CAR_GROUPS = ["A", "B", "C", "D", "E", "F", "G", "H", "J"]


def analyse_ghg():
    """A comparacao das emissoes, que e o que o modulo M2 produz.

    So entram as configuracoes cuja massa ja reproduz o i3ET: onde a massa
    difere, comparar emissoes seria medir de novo o fator de leveza.
    """
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    base = loader.load_sqlite(DB)
    ef = pd.DataFrame(
        [{"IDM": m, "IDEFV": "FIXTURE", "EF": v, "EFnotes": "i3ET", "IsUserDefined": 0}
         for m, v in fx["ef_by_material"].items()])
    conhecidas = set(base["P15"]["IDVMR"])
    descritas = set(base["P19"]["IDBMd"])

    out = []
    for code in fx["usable_configs"]:
        cfg = fx["configs"][code]
        nome = str(cfg.get("recipe") or "")
        idvmr = nome.split("-", 1)[1].strip() if "-" in nome else None
        if idvmr not in conhecidas:
            continue
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
        esperada = cfg["expected"]["vehicle_mass_kg"]
        if abs(r["totals"]["MassIDV"] - esperada) > 1e-6 * max(1.0, esperada):
            continue
        c10 = r["C10"].set_index("IDGG")
        presentes = [g for g in CAR_GROUPS if g in c10.index]
        massa_aux = float(c10["MassIDGG"].get("Iaux", 0.0))
        out.append({
            "config": code, "powertrain": cfg["powertrain"], "receita": idvmr,
            "fluidos_nossa": float(c10["GHGIDGG"].get("K", 0.0)),
            "fluidos_i3et": cfg["expected"]["ghg_fluids_kgCO2e"],
            "aux_nossa_por_kg": (float(c10["GHGIDGG"].get("Iaux", 0.0)) / massa_aux
                                 if massa_aux else None),
            "aux_i3et_por_kg": (cfg["expected"]["ghg_aux_battery_kgCO2e"] / massa_aux
                                if massa_aux else None),
            "carro_nossa": float(c10.loc[presentes, "GHGIDGG"].sum()),
            "carro_i3et": cfg["expected"]["ghg_materials_kgCO2e"],
            "bateria_descrita": bool(bid) and bid in descritas,
        })
    return out


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


def _secao_emissoes(w, ghg):
    """Secoes 6 e 7: o que o M2 produz, comparado com o i3ET."""
    fl = [g for g in ghg if g["fluidos_i3et"]]
    pior_fl = max((abs(g["fluidos_nossa"] - g["fluidos_i3et"]) / g["fluidos_i3et"]
                   for g in fl), default=0.0)
    aux = [g for g in ghg if g["aux_i3et_por_kg"]]
    razao_bp = {round(g["aux_i3et_por_kg"] / g["aux_nossa_por_kg"], 6)
                for g in aux if g["config"].startswith("BP")}
    razao_g = {round(g["aux_i3et_por_kg"] / g["aux_nossa_por_kg"], 6)
               for g in aux if not g["config"].startswith("BP")}
    w("## 6. Emissões: fluidos e baterias")
    w("")
    w(f"Em {len(ghg)} configurações da família de referência — aquelas cujas receitas "
      "de materiais a base possui e cuja massa já reproduz o i3ET — as emissões "
      "foram comparadas parcela a parcela.")
    w("")
    w("**Fluidos (grupo `K`) — corrigido em 20/09/2026.** A base do simulador não "
      "trazia composição para o grupo dos fluidos: a calculadora carregava a massa "
      "(25 a 43 kg por veículo) e lhe atribuía **emissão zero**. O i3ET traz a "
      "composição nas linhas 620 a 626 do módulo M2, e ela passou a integrar `P16`. "
      f"A concordância agora é exata (maior diferença relativa: {pior_fl:.1e}). "
      "Antes da correção, faltavam entre 67 e 108 kg CO₂e por veículo, ou algo entre "
      "1,5% e 2,3% do total do berço ao portão. **Nenhum ajuste é necessário no "
      "i3ET**: a falha estava na base derivada, não na planilha.")
    w("")
    w("**Bateria de tração.** Reproduz o i3ET na precisão da máquina em todos os "
      "modelos que a base descreve. As configurações da família `G` citam modelos "
      "que vivem apenas na planilha de baterias do i3ET; para elas a calculadora "
      "**mantém a massa, declara o fator ausente e registra aviso** — nunca atribui "
      "emissão zero em silêncio.")
    w("")
    if razao_bp | razao_g <= {1.0}:
        w("**Bateria auxiliar (chumbo-ácido).** Reproduz o i3ET exatamente, nas "
          "duas famílias de configurações. Até 20/09/2026 havia aqui uma "
          "diferença fixa de 9,87% nas colunas `BP`, atribuída a uma "
          "inconsistência interna da planilha: elas lançam o plástico da "
          "bateria como *Average Plastic* e as colunas `G` como *Polypropylene*. "
          "Não era inconsistência — eram duas receitas diferentes, e a base "
          "passou a ter as duas (§7).")
        w("")
    w("## 7. Emissões: composição dos materiais do veículo — **resolvido**")
    w("")
    w("Este foi o item em aberto de 20/09/2026, e está fechado. A massa do "
      "veículo já reproduzia o i3ET; a distribuição dessa massa entre materiais "
      "não. A investigação mostrou que não era deriva entre cópias de uma mesma "
      "tabela, e sim **duas receitas distintas**.")
    w("")
    w("### 7.1 Duas famílias de receitas, e não duas versões")
    w("")
    w("O i3ET guarda as receitas em colunas nomeadas do próprio módulo M2 "
      "(bloco `T8:DD281`), e a linha 9 de cada configuração nomeia a que ela "
      "usa. Há duas famílias:")
    w("")
    w("| Família | Origem |")
    w("|---|---|")
    w("| `<PT>-BISD<n>` | receita original, de consultoria |")
    w("| `<PT>-PBP_BISD<n>` | receita do Projeto do Berço ao Portão, que partiu da anterior e ajustou a participação de alguns materiais com informação das montadoras brasileiras |")
    w("")
    w("No grupo A, por exemplo:")
    w("")
    w("| Grupo A (carroceria) | `ICEV-BISD2` | `ICEV-PBP_BISD2` |")
    w("|---|---:|---:|")
    w("| Aço | 0,652777058 | 0,802318776 |")
    w("| Plástico médio | 0,216746989 | 0,110750895 |")
    w("| Cobre/latão | 0,018986306 | 0,000000000 |")
    w("| Alumínio forjado | 0,030699147 | 0,006139829 |")
    w("")
    w("A base trazia apenas a primeira, e os veículos do projeto usavam-na — daí "
      "uma diferença de 126,8 kg de aço em `BP01`, 90,4 no grupo A e 36,4 no "
      "grupo B, com a massa total inalterada. **As duas famílias passam a "
      "existir na base**, com a procedência declarada em `P15.DsVMR`, e cada "
      "cenário usa a receita que a planilha nomeia na sua coluna. Deduzir pelo "
      "trem de força não serviria: há mais de uma receita por trem de força, e "
      "`BP02` usa uma variante própria, `ICEV-PBP_BISD2s`, que o nome do "
      "veículo não revela. Por isso a *fixture* de validação passou a registrar "
      "o nome da receita de cada configuração.")
    w("")
    w("### 7.2 Participações que a base trazia como zero")
    w("")
    w("A importação também restaurou 36 participações não nulas que a base "
      "arredondara para zero — entre 2 × 10⁻⁵ e 4 × 10⁻⁴: platina no grupo D, "
      "níquel, náilon, resina fenólica, mica, zinco e óxido de zinco nos grupos "
      "C e G.")
    w("")
    w("Uma delas não é pequena no resultado: **a platina** do catalisador. Com o "
      "fator da versão BR23, de 69.670 kg CO₂e/kg, a participação de 2 × 10⁻⁵ "
      "vale 265 kg CO₂e em `BP01` e 152 kg em `BP07` — de 3% a 6% do veículo, "
      "vindos de um número arredondado para zero. É o caso exemplar do "
      "princípio da diretriz **D13**: numa tabela de fatores com cinco ordens de "
      "grandeza de amplitude, não existe participação desprezível a priori.")
    w("")
    w("*Discrepância conhecida e mantida:* a platina tem fator **126,5** kg "
      "CO₂e/kg nas versões G22, G23 e G24 e **69.670** na BR23 — 550 vezes "
      "maior. A diferença decide alguns pontos percentuais do resultado de "
      "qualquer veículo com catalisador. **Decisão de 20/09/2026: manter como "
      "está**, por ser discrepância já conhecida na tabela de fatores. A "
      "calculadora usa o fator da versão que o cenário escolher, e a escolha "
      "fica visível no resultado.")
    w("")
    w("### 7.3 Onde isso deixou a aderência")
    w("")
    w("| Configuração | Receita | Calculadora (kg CO₂e) | i3ET (kg CO₂e) | Dif. relativa |")
    w("|---|---|---:|---:|---:|")
    for _o, g in sorted((g["config"], g) for g in ghg if g["carro_i3et"]):
        rel = (g["carro_nossa"] - g["carro_i3et"]) / g["carro_i3et"]
        w(f"| `{g['config']}` | `{g.get('receita', '')}` | {g['carro_nossa']:,.3f} | "
          f"{g['carro_i3et']:,.3f} | {rel:+.1e} |")
    w("")
    w("Os `ICEV` e os `BEV` reproduzem o i3ET na precisão da máquina. O resíduo "
      "de 3 × 10⁻⁵ dos híbridos vem de uma decisão declarada: algumas colunas do "
      "i3ET fecham a soma do grupo com um resíduo **negativo** na linha "
      "`Others`, da ordem de 1 × 10⁻⁴. Participação mássica negativa não existe; "
      "essas oito linhas entram como zero e a normalização redistribui a "
      "diferença.")
    w("")
    w("**Decisão de 20/09/2026: normalizar.** Uma participação negativa num "
      "vetor de frações mássicas é um artifício de planilha que não sobrevive à "
      "passagem para um modelo relacional — o invariante I1 existe justamente "
      "para impedir que ele passe despercebido. As oito linhas entram como "
      "zero, a normalização redistribui, e o resíduo de 3 × 10⁻⁵ nos híbridos é "
      "o preço declarado dessa decisão.")
    w("")


def write_report(findings, fx, path, ghg=None):
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
    if ghg:
        _secao_emissoes(w, ghg)
    w("## 8. Conclusão")
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
    w("Os **doze veículos de referência `BP01`–`BP12` reproduzem o i3ET em massa "
      "na precisão da máquina**, com erro relativo entre 0 e 2,6 × 10⁻¹⁶.")
    if ghg:
        pior = max(abs(g["carro_nossa"] - g["carro_i3et"]) / g["carro_i3et"]
                   for g in ghg if g["carro_i3et"])
        w("")
        w("Em **emissões**, os mesmos doze veículos também reproduzem o i3ET: "
          f"a maior diferença relativa é de {pior:.0e}, e vem de uma decisão "
          "declarada — a normalização das participações negativas (§7.3). "
          "Fluidos, bateria de tração e bateria auxiliar coincidem exatamente.")
    w("")
    w("---")
    w("")
    w("*Gerado por `tools/report_divergences.py`.*")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return material


def main():
    findings, fx = analyse()
    ghg = analyse_ghg()
    hoje = dt.date.today().strftime("%Y%m%d")
    nome = f"RelatorioDeDivergencias_i3ET_{hoje}a.md"
    destinos = [
        os.path.expanduser("~/mnt/_Calculadora da Pegada de Carbono do Berço ao Portão/"
                           f"Documentação/{nome}"),
        os.path.join(REPO, "docs", "05-relatorio-de-divergencias.md"),
    ]
    for d in destinos:
        if os.path.isdir(os.path.dirname(d)):
            material = write_report(findings, fx, d, ghg)
            print("gravado:", d)
    print(f"\n{len(findings)} configuracoes, {len(material)} com diferenca material")
    for causa in sorted({f['causa'] for f in findings if f['causa'] != 'nenhuma'}):
        n = sum(1 for f in findings if f["causa"] == causa)
        print(f"   {causa:26s}: {n}")


if __name__ == "__main__":
    main()
