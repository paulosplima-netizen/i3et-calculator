"""Regras de valor padrao dos parametros de veiculo (Fase A, passo 4).

P35 guarda uma regra por celula preenchida da matriz da Market Vehicles
(M257:AW299). Para um veiculo e um parametro vale a primeira regra, na ordem de
`RuleSeq`, cujos criterios preenchidos sao todos atendidos; criterio nulo nao
restringe. A versao `TAB` e a regra como tabulada; a que as formulas da
planilha gravaram esta em P27, classe `Def`, e a T11 mostra as duas.

O criterio de faixa de potencia da matriz esta em hp, e a potencia do motor a
combustao (parametro 2) esta em kW. O fator de conversao e argumento, nao
constante do calculo: 1,34102 hp/kW foi o que reproduziu a matriz sem
divergencia (1,35962 deixa 2 veiculos fora no parametro 4).

Blocos:
    VD1  avaliar as regras de P35 para um veiculo
    VD2  comparar com o valor gravado em P27

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

#: Valor que reproduz a matriz; passado como argumento a quem chama.
HP_PER_KW = 1.34102

#: Parametros da Market Vehicles de que as regras dependem.
IDMP_POWER_ICE = 2     # kW
IDMP_AREA = 9          # m2


@dataclass(frozen=True)
class Rule:
    seq: int
    powertrain: str | None
    design: str | None
    size: str | None
    luxury: str | None
    power_min_hp: float | None
    power_max_hp: float | None
    area_min: float | None
    area_max: float | None
    value: float | None
    text: str | None
    factor_of: int | None


# --------------------------------------------------------------------------
# BLOCO VD1 -- avaliar as regras
#   Le      : P35 (versao escolhida).
#   Devolve : {IDMP: [Rule, ...]} e o valor padrao de um veiculo.
# --------------------------------------------------------------------------
def load_rules(conn: sqlite3.Connection, version: str = "TAB") -> dict[int, list[Rule]]:
    rules: dict[int, list[Rule]] = {}
    for row in conn.execute(
            "SELECT IDMP, RuleSeq, IDVPT, IDVDT, IDVS, IDLR, PowerMinHP, PowerMaxHP, "
            "AreaMin, AreaMax, Value, ValueText, FactorOfIDMP "
            "FROM P35_VehicleParamDefaultRule WHERE IDDRV = ? ORDER BY IDMP, RuleSeq",
            (version,)):
        rules.setdefault(row[0], []).append(Rule(*row[1:]))
    return rules


def _matches(rule: Rule, v: dict, ice_hp: float, area: float | None) -> bool:
    if rule.powertrain and rule.powertrain != v["IDVPT"]:
        return False
    if rule.design and rule.design != v["IDVDT"]:
        return False
    if rule.size and rule.size != v["IDVS"]:
        return False
    if rule.luxury and rule.luxury != v["IDLR"]:
        return False
    if rule.power_min_hp is not None and not ice_hp >= rule.power_min_hp:
        return False
    if rule.power_max_hp is not None and not ice_hp < rule.power_max_hp:
        return False
    if rule.area_min is not None and not (area is not None and area >= rule.area_min):
        return False
    if rule.area_max is not None and not (area is not None and area < rule.area_max):
        return False
    return True


def default_value(rules: dict[int, list[Rule]], vehicle: dict, idmp: int, *,
                  hp_per_kw: float) -> float | str | None:
    """Valor padrao de `idmp` para o veiculo, ou None se nenhuma regra serve.

    `vehicle` traz IDVPT, IDVDT, IDVS, IDLR e `params` ({IDMP: valor}), com a
    potencia do motor a combustao (2, em kW) e a area (9, em m2).
    """
    params = vehicle.get("params", {})
    ice_hp = float(params.get(IDMP_POWER_ICE) or 0.0) * hp_per_kw
    area = params.get(IDMP_AREA)
    for rule in rules.get(idmp, []):
        if not _matches(rule, vehicle, ice_hp, area):
            continue
        if rule.value is None:
            return rule.text
        if rule.factor_of is not None:
            base = params.get(rule.factor_of)
            return None if base is None else rule.value * float(base)
        return rule.value
    return None


# --------------------------------------------------------------------------
# BLOCO VD2 -- comparar com P27
#   Le      : P26, P27 (classe `Def`) e as regras.
#   Devolve : por parametro, quantos veiculos de classe `Def` divergem da regra
#             tabulada e quantos ficam sem regra (T11).
# --------------------------------------------------------------------------
def _vehicles(conn: sqlite3.Connection) -> list[dict]:
    out: dict[int, dict] = {}
    for idmv, pt, dt, vs, lr in conn.execute(
            "SELECT IDMV, IDVPT, IDVDT, IDVS, IDLR FROM P26_MarketVehicle WHERE IsSelecao = 0"):
        out[idmv] = {"IDMV": idmv, "IDVPT": pt, "IDVDT": dt, "IDVS": vs, "IDLR": lr,
                     "params": {}, "classes": {}}
    for idmv, idmp, val, txt, cls in conn.execute(
            "SELECT IDMV, IDMP, Value, ValueText, ValueClass FROM P27_MarketVehicleParam"):
        if idmv in out:
            out[idmv]["params"][idmp] = val if val is not None else txt
            out[idmv]["classes"][idmp] = cls
    return list(out.values())


def compare(conn: sqlite3.Connection, *, hp_per_kw: float,
            version: str = "TAB") -> dict[int, dict[str, int]]:
    rules = load_rules(conn, version)
    result = {idmp: {"checked": 0, "differ": 0, "no_rule": 0} for idmp in rules}
    for v in _vehicles(conn):
        for idmp in rules:
            if v["classes"].get(idmp) != "Def":
                continue
            res = result[idmp]
            res["checked"] += 1
            want = default_value(rules, v, idmp, hp_per_kw=hp_per_kw)
            got = v["params"].get(idmp)
            if want is None:
                res["no_rule"] += 1
            elif isinstance(want, str) or isinstance(got, str):
                res["differ"] += want != got
            else:
                res["differ"] += abs(want - got) > 1e-6
    return result
