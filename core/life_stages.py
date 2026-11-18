"""Vida do veiculo por estagio (T18; C35; M2 T511).

Bloco B1. Sem Streamlit. Reune, numa tabela de rastreio, o que a planilha soma em

    T511 = T495 + T509 + T510 + T516 + T560 + T571 + T617

nos tres estagios do protótipo T18:

    INITIAL_PRODUCTION     T516 materiais (sem baterias e fluidos), T560 bateria
                           auxiliar, T571 bateria de tracao, T617 fluidos, T510 montagem
    LIFETIME_REPLACEMENTS  T495 (pneus, bateria auxiliar, bateria de tracao, fluidos)
    END_OF_LIFE            T509

A producao inicial e o resultado do berco ao portao de hoje (materiais e montagem);
os outros dois estagios vem de core/maintenance.py e core/endoflife.py.
"""

from __future__ import annotations

import pandas as pd

STAGES = ("INITIAL_PRODUCTION", "LIFETIME_REPLACEMENTS", "END_OF_LIFE")
AUX, TRACTION, FLUIDS = "Iaux", "Iprinc", "K"


def group_ghg(c10: pd.DataFrame, idgg: str) -> float:
    return float(c10.loc[c10["IDGG"] == idgg, "GHGIDGG"].sum())


def build(*, c10: pd.DataFrame, assembly_kg: float, replacements: dict | None,
          eol: dict | None, include_assembly: bool = True) -> list[dict]:
    """Linhas de C35 (sem RunID, IDA, IDCase, IDV: quem grava acrescenta)."""
    materiais = float(c10.loc[~c10["IDGG"].isin([AUX, TRACTION, FLUIDS]), "GHGIDGG"].sum())
    linhas = [
        ("INITIAL_PRODUCTION", "MATERIALS", materiais, "M2 T516", "recipe x EF list",
         "Materiais dos grupos, sem baterias e fluidos"),
        ("INITIAL_PRODUCTION", "AUX_BATTERY", group_ghg(c10, AUX), "M2 T560", "recipe x EF list",
         "Bateria auxiliar (chumbo-acido)"),
        ("INITIAL_PRODUCTION", "TRACTION_BATTERY", group_ghg(c10, TRACTION), "M2 T571",
         "battery model x EF list", "Bateria de tracao"),
        ("INITIAL_PRODUCTION", "FLUIDS", group_ghg(c10, FLUIDS), "M2 T617", "recipe x EF list",
         "Fluidos iniciais"),
        ("INITIAL_PRODUCTION", "ASSEMBLY", float(assembly_kg) if include_assembly else 0.0,
         "M2 T510", "assembly version", "Montagem do veiculo"
         + ("" if include_assembly else " (fora da fronteira escolhida)")),
    ]
    if replacements is not None:
        nomes = {"tires": "TIRES", "aux_battery": "AUX_BATTERY",
                 "traction_battery": "TRACTION_BATTERY", "fluids": "FLUIDS"}
        celulas = {"tires": "T496", "aux_battery": "T499", "traction_battery": "T500",
                   "fluids": "T501"}
        for chave, sub in nomes.items():
            linhas.append(("LIFETIME_REPLACEMENTS", sub, float(replacements["components"][chave]),
                           f"M2 {celulas[chave]}", "interval x events",
                           "Reposicoes por quilometragem"))
    if eol is not None:
        linhas.append(("END_OF_LIFE", eol["EoLMethod"], float(eol["GHGEoL"]), "M2 T509",
                       eol["EoLMethod"], "Fim de vida pelo metodo escolhido"))
    return [dict(Stage=s, SubStage=sub, GHGkg=g, SourceCell=c, Method=m, Note=n)
            for s, sub, g, c, m, n in linhas]


def totals(rows: list[dict]) -> dict:
    """Total por estagio e total geral (T511)."""
    por = {s: sum(r["GHGkg"] for r in rows if r["Stage"] == s) for s in STAGES}
    por["TOTAL"] = sum(por[s] for s in STAGES)
    return por
