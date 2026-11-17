"""Fatores de emissao de uma versao do GREET aplicados a receita de outra.

Fase A, passo 4 (divergencia D2). Ate o GREET 2022 ha um so tipo de aluminio
(IDM 4); do GREET 2023 em diante ha chapa (4a) e extrudado (4b), e as receitas
seguem a mesma divisao. Como a lista de fatores e a receita sao escolhidas de
forma independente, as versoes podem nao combinar. `P57` diz quais materiais
se correspondem e com que peso; este modulo aplica o criterio:

    1. A receita usa os tipos novos (filhos) e a lista so tem o tipo unico
       (pai): cada filho recebe o fator do pai. Alerta.
    2. A receita usa o tipo unico (pai) e a lista so tem os tipos novos
       (filhos): o pai recebe a media ponderada dos fatores dos filhos, com os
       pesos de `P57`. Alerta.
    3. Qualquer outro material sem fator continua ausente, nunca zero (a
       linha de C03 fica com HasFactor = 0, como ja era).

O i3ET em Excel aloca zero aos tipos novos no caso 1; a calculadora nao
(divergencia D2, docs/05a). Nada aqui e constante de codigo: pares e pesos
vem de P57.

Blocos:
    EQ1  pares e pesos (P57)
    EQ2  adaptacao da tabela de fatores e alertas

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import pandas as pd

#: Regra de validacao do alerta (docs/07).
RULE = "I28"


# --------------------------------------------------------------------------
# BLOCO EQ1 -- pares e pesos
#   Le      : P57 como DataFrame (IDMParent, IDMChild, Weight).
#   Devolve : {pai: {filho: peso}}.
# --------------------------------------------------------------------------
def groups(p57: pd.DataFrame | None) -> dict[str, dict[str, float]]:
    if p57 is None or p57.empty:
        return {}
    out: dict[str, dict[str, float]] = {}
    for _, r in p57.iterrows():
        out.setdefault(str(r["IDMParent"]), {})[str(r["IDMChild"])] = float(r["Weight"])
    return out


def _has(v) -> bool:
    return v is not None and not pd.isna(v)


# --------------------------------------------------------------------------
# BLOCO EQ2 -- adaptacao
#   Le      : a tabela de fatores efetiva, a versao escolhida, os materiais que
#             o veiculo usa (receita e bateria) e P57.
#   Devolve : (tabela com os fatores adaptados, lista de alertas). As linhas
#             adaptadas levam IsAdapted = 1 e o motivo em EFnotes. A tabela de
#             entrada nao e alterada.
# --------------------------------------------------------------------------
def adapt(ef_table: pd.DataFrame, idefv: str, used: set[str],
          p57: pd.DataFrame | None, log=None, context: str | None = None
          ) -> tuple[pd.DataFrame, list[dict]]:
    table = ef_table.copy()
    if "IsAdapted" not in table.columns:
        table["IsAdapted"] = 0
    alerts: list[dict] = []
    grp = groups(p57)
    if not grp:
        return table, alerts

    mine = table[table["IDEFV"] == idefv]
    factor = {str(r["IDM"]): r["EF"] for _, r in mine.iterrows()}
    novos: dict[str, tuple[float, str]] = {}

    for pai, filhos in grp.items():
        # Caso 1: receita nos tipos novos, lista no tipo unico.
        for filho in filhos:
            if filho in used and not _has(factor.get(filho)) and _has(factor.get(pai)):
                valor = float(factor[pai])
                nota = (f"Fator adaptado: a versao {idefv} nao separa o material {filho}; "
                        f"usado o do material {pai} ({valor:.4f}).")
                novos[filho] = (valor, nota)
                alerts.append({"rule": RULE, "kind": "ParentToChild", "IDEFV": idefv,
                               "IDM": filho, "IDMSource": pai, "EF": valor})
        # Caso 2: receita no tipo unico, lista nos tipos novos.
        if pai in used and not _has(factor.get(pai)) \
                and all(_has(factor.get(f)) for f in filhos):
            soma = sum(filhos.values())
            valor = sum(w * float(factor[f]) for f, w in filhos.items()) / soma
            nota = (f"Fator adaptado: a versao {idefv} separa o material {pai} em "
                    + " e ".join(filhos) + "; usada a media ponderada pelos pesos de P57 "
                    f"({valor:.4f}).")
            novos[pai] = (valor, nota)
            alerts.append({"rule": RULE, "kind": "ChildrenToParent", "IDEFV": idefv,
                           "IDM": pai, "IDMSource": ",".join(filhos), "EF": valor})

    for idm, (valor, nota) in novos.items():
        mask = (table["IDEFV"] == idefv) & (table["IDM"].astype(str) == idm)
        if mask.any():
            table.loc[mask, ["EF", "EFnotes", "IsAdapted"]] = [valor, nota, 1]
        else:
            linha = {c: None for c in table.columns}
            linha.update({"IDM": idm, "IDEFV": idefv, "EF": valor, "EFnotes": nota,
                          "IsAdapted": 1})
            table = pd.concat([table, pd.DataFrame([linha])], ignore_index=True)

    if log is not None:
        for a in alerts:
            if a["kind"] == "ParentToChild":
                msg = (f"versao de fatores {idefv} nao tem o material {a['IDM']}, que a "
                       f"receita usa; adotado o fator do material {a['IDMSource']} "
                       f"({a['EF']:.4f})")
            else:
                msg = (f"versao de fatores {idefv} separa o material {a['IDM']} em "
                       f"{a['IDMSource']}, que a receita nao usa; adotada a media ponderada "
                       f"({a['EF']:.4f})")
            log.warn(RULE, msg, context)
    return table, alerts
