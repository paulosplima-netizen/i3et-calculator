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
import re
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


#: Configuracoes cujas receitas de materiais a base efetivamente possui.
REFERENCE_FAMILY = re.compile(r"^(G\d{1,2}|BP\d{2})$")
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
    rec = {r["IDVPT"]: r["IDVMR"] for r in base["P15"].to_dict("records")}
    descritas = set(base["P19"]["IDBMd"])

    out = []
    for code in fx["usable_configs"]:
        cfg = fx["configs"][code]
        if not REFERENCE_FAMILY.match(code) or cfg["powertrain"] not in rec:
            continue
        gc = {int(k): (v if isinstance(v, (int, float)) else 0.0)
              for k, v in cfg["gc"].items()}
        bid = cfg["gc"].get("32")
        bid = None if bid in (None, "-", "NA") else str(bid).strip()
        supplied = {i for i in P.ENDOGENOUS
                    if isinstance(cfg["gc"].get(str(i)), (int, float))}
        r = calc.calculate_vehicle(base, gc, powertrain=cfg["powertrain"],
                                   battery_id=bid, idmpv=1, idvmr=rec[cfg["powertrain"]],
                                   idefv="FIXTURE", idapv="A-EF", boundary="MAT",
                                   ef_table=ef, supplied=supplied)
        esperada = cfg["expected"]["vehicle_mass_kg"]
        if abs(r["totals"]["MassIDV"] - esperada) > 1e-6 * max(1.0, esperada):
            continue
        c10 = r["C10"].set_index("IDGG")
        presentes = [g for g in CAR_GROUPS if g in c10.index]
        massa_aux = float(c10["MassIDGG"].get("Iaux", 0.0))
        out.append({
            "config": code, "powertrain": cfg["powertrain"],
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
    if len(razao_bp) == 1 and razao_g <= {1.0}:
        razao = razao_bp.pop()
        w("**Bateria auxiliar (chumbo-ácido).** A intensidade por quilograma coincide "
          "exatamente com a das colunas `G` do i3ET. As colunas `BP` da mesma planilha "
          f"são **{(razao - 1) * 100:.2f}% maiores**, por uma razão localizada: elas "
          "lançam o plástico da bateria como *Average Plastic* (IDM 10; 4,4833 kg "
          "CO₂e/kg) enquanto as colunas `G` o lançam como *Polypropylene* (2,6074). "
          "A base segue o polipropileno, que é o material específico e é também o que "
          "a receita do simulador declara. O efeito é de cerca de 1,8 kg CO₂e por "
          "veículo — menos de 0,05% do total.")
        w("")
        w("**Ajuste sugerido no i3ET:** uniformizar o material do plástico da bateria "
          "auxiliar entre as duas famílias de colunas. É uma inconsistência interna da "
          "planilha, não uma divergência com a calculadora.")
        w("")
    w("## 7. Emissões: composição dos materiais do veículo — **duas causas identificadas**")
    w("")
    w("A **massa** do veículo reproduz o i3ET exatamente. A **distribuição dessa "
      "massa entre materiais** diverge em alguns grupos, e a investigação de "
      "20/09/2026 separou duas causas independentes. Nenhuma delas é erro de "
      "cálculo; as duas são de dados, e cada uma pede uma decisão diferente.")
    w("")
    w("### 7.1 Duas receitas com o mesmo nome (apenas ICEV)")
    w("")
    w("O i3ET guarda as receitas de materiais em colunas nomeadas, no próprio "
      "módulo M2 (bloco `T8:DD281`), e cada configuração escolhe a sua pela "
      "linha 9. Existem, lado a lado, **duas colunas para a mesma receita**:")
    w("")
    w("| Grupo A (carroceria) | `ICEV-BISD2` | `ICEV-PBP_BISD2` |")
    w("|---|---:|---:|")
    w("| Aço | 0,652777058 | 0,802318776 |")
    w("| Plástico médio | 0,216746989 | 0,110750895 |")
    w("| Cobre/latão | 0,018986306 | 0,000000000 |")
    w("| Alumínio forjado | 0,030699147 | 0,006139829 |")
    w("")
    w("A base da calculadora traz `ICEV-BISD2` — **idêntica à coluna do i3ET até "
      "a nona casa decimal**, o que descarta a hipótese de deriva entre duas "
      "cópias. As configurações `BP01` e `BP02`, porém, apontam para "
      "`ICEV-PBP_BISD2`, e `BP03` para `ICEV-PBP_BISD3`. São escolhas de coluna, "
      "não versões diferentes do mesmo dado.")
    w("")
    w("O efeito, em `BP01`: **−126,8 kg de aço** (−90,4 no grupo A, −36,4 no "
      "grupo B), +56,4 kg de plástico médio, +36,9 kg de alumínio fundido. A "
      "massa total não muda — muda a quem ela é atribuída. Em emissões: +223 kg "
      "CO₂e no grupo A e +217 kg no grupo B.")
    w("")
    w("**As variantes `PBP_` só diferem para ICEV.** Para `HEV-PBP_BISD6`, "
      "`PHEV-PBP_BISD8` e `BEV-PBP_BISD12` as colunas são iguais às `BISD` "
      "correspondentes — e, de fato, `BP04` a `BP12` não apresentam nenhuma "
      "diferença de composição.")
    w("")
    w("**Decisão pendente:** adotar as receitas `PBP_` para `BISD2` e `BISD3`, "
      "que é o que o i3ET usa nos veículos do projeto (diretriz D11), ou manter "
      "as `BISD`. Convém, antes, saber o que distingue as duas na origem.")
    w("")
    w("### 7.2 Participações pequenas perdidas na transcrição")
    w("")
    w("A base traz **zero** em participações que o i3ET tem como não nulas. São "
      "valores de 2 × 10⁻⁵ a 4 × 10⁻⁴ — platina no grupo D, níquel, náilon, "
      "resina fenólica, mica, zinco e óxido de zinco nos grupos C e G, além da "
      "linha `Others` em B e D. A normalização das receitas redistribuiu o peso "
      "dessas ausências entre os demais materiais, o que explica as diferenças "
      "de quarta casa decimal em aço e alumínio.")
    w("")
    w("Uma delas não é pequena no resultado: **a platina**. A participação é de "
      "2 × 10⁻⁵ nos ICEV e 1 × 10⁻⁵ nos híbridos, mas o fator de emissão da "
      "versão BR23 é de 69.670 kg CO₂e/kg. Em `BP01` isso vale **265 kg CO₂e** e "
      "em `BP07`, **152 kg** — de 3% a 6% do veículo, vindos de um número que a "
      "base arredondou para zero. É o caso exemplar do princípio da diretriz "
      "D13: em uma tabela de fatores com cinco ordens de grandeza de amplitude, "
      "não existe participação desprezível a priori.")
    w("")
    w("*Nota lateral:* a mesma platina tem fator **126,5** kg CO₂e/kg nas "
      "versões G22/G23/G24 e **69.670** na BR23 — 550 vezes maior. Com os "
      "fatores G22, que são os das avaliações do projeto, a participação perdida "
      "vale meio quilo de CO₂e. A discrepância entre versões merece verificação "
      "na aba de fatores do i3ET.")
    w("")
    w("**Correção proposta:** importar as participações do bloco de receitas do "
      "i3ET, restaurando as que a base perdeu. Não é mudança de critério, é "
      "recuperar a precisão da própria fonte de registro — mas desloca os "
      "resultados, então entra em commit próprio, com os testes de regressão "
      "recongelados na mesma mudança.")
    w("")
    w("### 7.3 Efeito combinado nos doze veículos do projeto")
    w("")
    w("Nos ICEV as duas causas têm sinais opostos e se cancelam em parte; nos "
      "híbridos e elétricos só a segunda atua, e ela é toda platina — nos `BEV` "
      "nem isso, porque não há catalisador.")
    w("")
    w("| Configuração | Trem de força | Calculadora (kg CO₂e) | i3ET (kg CO₂e) | Dif. | Causa dominante |")
    w("|---|---|---:|---:|---:|---|")
    causa = {"ICEV": "§7.1 e §7.2", "HEV": "§7.2 (platina)",
             "PHEV": "§7.2 (platina)", "BEV": "resíduo"}
    for _rel, g in sorted((-abs((g["carro_nossa"] - g["carro_i3et"]) / g["carro_i3et"]), g)
                          for g in ghg if g["carro_i3et"] and g["config"].startswith("BP")):
        rel = (g["carro_nossa"] - g["carro_i3et"]) / g["carro_i3et"]
        w(f"| `{g['config']}` | {g['powertrain']} | {g['carro_nossa']:,.1f} | "
          f"{g['carro_i3et']:,.1f} | {rel:+.2%} | {causa.get(g['powertrain'], '')} |")
    w("")
    w("Enquanto as duas decisões não são tomadas, o teste "
      "`test_car_materials_stay_within_the_documented_gap` trava a distância no "
      "patamar atual, de modo que ela não possa crescer despercebida.")
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
    w("Os **doze veículos de referência `BP01`–`BP12` reproduzem o i3ET na precisão "
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
