"""Reposicoes ao longo da vida do veiculo (T16; M2 T495).

Bloco B1. Sem Streamlit. Cada item de P31 tem um intervalo de reposicao em km;
os eventos ocorrem em k x intervalo, para k = 1, 2, ..., desde que
k x intervalo < L, a vida do veiculo (nao ha reposicao no fim da vida). A
planilha traz so a contagem (T496 a T501); aqui a contagem e calculada e cada
evento e uma linha de C15.

    T495 = I x (T496 + T499 + J x T500 + T501)
    I = 1 se o modo e "Sim" ou "Sim Bat" (0 em "Nao"); J = 1 so em "Sim Bat".

Blocos:
    MT1  numero de eventos de um item
    MT2  GHG de um evento, por tipo de item
    MT3  calculo completo (eventos, totais por item e total)
"""

from __future__ import annotations

import math

MODES = ("Sim", "Sim Bat", "Não")
IAUX, IPRINC = "Iaux", "Iprinc"


# --------------------------------------------------------------------------
# BLOCO MT1 -- eventos
# --------------------------------------------------------------------------
def event_count(life_km: float, interval_km: float | None) -> int:
    """n = numero de k >= 1 com k x intervalo < L (I39). Sem intervalo ou L <= 0: 0."""
    if not interval_km or interval_km <= 0 or life_km <= 0:
        return 0
    q = life_km / interval_km
    r = round(q)
    return r - 1 if abs(q - r) < 1e-9 else math.floor(q)


# --------------------------------------------------------------------------
# BLOCO MT2 -- GHG de um evento
#   PART     massa do conjunto x soma(participacao x FE do material)
#   BATTERY  GHG de producao do grupo da bateria no veiculo
#   FLUID    FE do fluido x massa do fluido no veiculo
# --------------------------------------------------------------------------
def event_ghg(item: dict, *, part_shares: dict[str, float], ef: dict[str, float],
              fluid_mass: dict[str, float], group_ghg: dict[str, float]) -> float:
    kind = item["ItemKind"]
    if kind == "PART":
        massa = float(item["MassPerUnitKg"])
        return massa * sum(sh * ef[idm] for idm, sh in part_shares.items())
    if kind == "BATTERY":
        return float(group_ghg.get(item["IDGG"], 0.0))
    return float(ef[item["IDM"]]) * float(fluid_mass.get(item["IDM"], 0.0))


# --------------------------------------------------------------------------
# BLOCO MT3 -- calculo
#   Le      : itens (linhas de P31, com IntervalKm possivelmente do usuario),
#             composicao dos conjuntos {IDMI: {IDM: share}}, FE {IDM: EF}, massa
#             dos fluidos {IDM: kg}, GHG por grupo {IDGG: kg}, modo e vida.
#   Devolve : {"events": [...], "by_item": {IDMI: GHG}, "components":
#             {"tires", "aux_battery", "traction_battery", "fluids"}, "total"}
# --------------------------------------------------------------------------
def replacements(items: list[dict], *, life_km: float, mode: str,
                 part_shares: dict[str, dict[str, float]], ef: dict[str, float],
                 fluid_mass: dict[str, float], group_ghg: dict[str, float],
                 active: dict[str, bool] | None = None) -> dict:
    if mode not in MODES:
        raise ValueError(f"modo de manutencao invalido: {mode!r}")
    eventos: list[dict] = []
    por_item: dict[str, float] = {}
    comp = {"tires": 0.0, "aux_battery": 0.0, "traction_battery": 0.0, "fluids": 0.0}
    if mode != "Não":
        for it in items:
            idmi = it["IDMI"]
            if active is not None and not active.get(idmi, True):
                continue
            if it["IDMI"] == "BATT_TRAC" and mode != "Sim Bat":
                continue
            n = event_count(life_km, it.get("IntervalKm"))
            g = event_ghg(it, part_shares=part_shares.get(idmi, {}), ef=ef,
                          fluid_mass=fluid_mass, group_ghg=group_ghg) if n else 0.0
            for k in range(1, n + 1):
                eventos.append({"IDMI": idmi, "EventIndex": k,
                                "EventKm": k * float(it["IntervalKm"]), "GHGkg": g})
            por_item[idmi] = n * g
            chave = {"PART": "tires", "FLUID": "fluids"}.get(it["ItemKind"])
            if chave is None:
                chave = "traction_battery" if idmi == "BATT_TRAC" else "aux_battery"
            comp[chave] += n * g
    return {"events": eventos, "by_item": por_item, "components": comp,
            "total": sum(comp.values())}
