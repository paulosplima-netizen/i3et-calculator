"""Potencia combinada: fatores de uso combinado dos motores (IDVP 15).

Fase A, passo 4. A potencia combinada de um veiculo e

    P = FatorICE * P_ICE + FatorEE * P_EE

onde P_ICE e a potencia do motor a combustao (IDVP 2) e P_EE a do motor
eletrico (IDVP 3). Os fatores sao parametros, nunca constantes de codigo:

    - ICEV usa so o motor a combustao (1; 0); BEV, FCEV, SHEV e SPHEV, so o
      eletrico (0; 1). Esses pares sao fixos e nao admitem ajuste.
    - HEV e PHEV tem um par padrao em P53 (provisorio: soma, (1; 1)) e, para as
      configuracoes gravadas na planilha, um par arbitrado em P56 para igualar o
      Excel. Depois da validacao os fatores serao arbitrados entre 0 e 1.
    - O usuario pode trocar o par de um caso de HEV ou PHEV (tabela D12).

Blocos:
    PR1  leitura dos fatores padrao (P53) e arbitrados (P56)
    PR2  ajuste do usuario (D12)
    PR3  fatores efetivos e potencia combinada

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

#: Motorizacoes cujo par de fatores nao pode ser trocado.
FIXED_POWERTRAINS = ("ICEV", "BEV", "FCEV", "SHEV", "SPHEV")

#: Regras da analise (D06.CombinedPowerRule).
RULES = ("Default", "ExcelParity")


@dataclass(frozen=True)
class Factors:
    ice: float
    ee: float
    origin: str            # 'Fixed', 'Default', 'ExcelFit' ou 'UserOverride'
    provisional: bool

    def combine(self, power_ice: float, power_ee: float) -> float:
        return self.ice * power_ice + self.ee * power_ee


def _check(ice: float, ee: float) -> None:
    for nome, v in (("FactorICE", ice), ("FactorEE", ee)):
        if not 0.0 <= float(v) <= 1.0:
            raise ValueError(f"{nome} must be between 0 and 1 (got {v})")


# --------------------------------------------------------------------------
# BLOCO PR1 -- fatores padrao e arbitrados
#   Le      : P53_CombinedPowerRule e P56_CombinedPowerFit.
#   Devolve : ({motorizacao: Factors}, {caso: Factors}).
# --------------------------------------------------------------------------
def load_defaults(conn: sqlite3.Connection) -> dict[str, Factors]:
    return {pt: Factors(ice, ee, "Fixed" if pt in FIXED_POWERTRAINS else "Default", bool(prov))
            for pt, ice, ee, prov in conn.execute(
                "SELECT IDVPT, FactorICE, FactorEE, IsProvisional FROM P53_CombinedPowerRule")}


def load_fits(conn: sqlite3.Connection) -> dict[str, Factors]:
    return {key: Factors(ice, ee, "Fixed" if kind == "Fixed" else "ExcelFit", bool(prov))
            for key, ice, ee, kind, prov in conn.execute(
                "SELECT CaseKey, FactorICE, FactorEE, FitKind, IsProvisional "
                "FROM P56_CombinedPowerFit")}


# --------------------------------------------------------------------------
# BLOCO PR2 -- ajuste do usuario
#   Le      : D12_CombinedPowerOverride de uma analise.
#   Devolve : {IDCase: Factors}.
# --------------------------------------------------------------------------
def load_overrides(conn: sqlite3.Connection, ida: int) -> dict[int, Factors]:
    return {case: Factors(ice, ee, "UserOverride", False)
            for case, ice, ee in conn.execute(
                "SELECT IDCase, FactorICE, FactorEE FROM D12_CombinedPowerOverride "
                "WHERE IDA = ?", (ida,))}


def set_override(conn: sqlite3.Connection, ida: int, idcase: int, ice: float, ee: float,
                 notes: str | None = None) -> None:
    """Grava o ajuste de um caso. So HEV e PHEV aceitam ajuste."""
    _check(ice, ee)
    row = conn.execute("SELECT IDVPT FROM D07_AnalysisVehicle WHERE IDA = ? AND IDCase = ?",
                       (ida, idcase)).fetchone()
    if row is None:
        raise ValueError(f"Case {idcase} does not exist in analysis {ida}")
    if row[0] in FIXED_POWERTRAINS:
        raise ValueError(f"The combined power of {row[0]} is fixed and cannot be changed")
    conn.execute(
        "INSERT INTO D12_CombinedPowerOverride (IDA, IDCase, FactorICE, FactorEE, NotesCPO) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT (IDA, IDCase) DO UPDATE SET "
        "FactorICE = excluded.FactorICE, FactorEE = excluded.FactorEE, "
        "NotesCPO = excluded.NotesCPO", (ida, idcase, ice, ee, notes))


def clear_override(conn: sqlite3.Connection, ida: int, idcase: int) -> None:
    """Restore default: apaga a linha de D12."""
    conn.execute("DELETE FROM D12_CombinedPowerOverride WHERE IDA = ? AND IDCase = ?",
                 (ida, idcase))


# --------------------------------------------------------------------------
# BLOCO PR3 -- fatores efetivos e potencia combinada
#   Ordem: ajuste do usuario; se a regra e ExcelParity e o caso tem par
#   arbitrado, esse par; senao o padrao da motorizacao. Motorizacao de par
#   fixo ignora a regra e usa sempre o padrao.
#   Devolve : Factors (com a origem, para o selo e para a rodada congelada).
# --------------------------------------------------------------------------
def effective_factors(powertrain: str, *, rule: str = "Default",
                      case_key: str | None = None, idcase: int | None = None,
                      defaults: dict[str, Factors], fits: dict[str, Factors] | None = None,
                      overrides: dict[int, Factors] | None = None) -> Factors:
    if rule not in RULES:
        raise ValueError(f"Unknown combined power rule: {rule}")
    if powertrain not in defaults:
        raise ValueError(f"No combined power factors for powertrain {powertrain}")
    if powertrain in FIXED_POWERTRAINS:
        return defaults[powertrain]
    if overrides and idcase in overrides:
        return overrides[idcase]
    if rule == "ExcelParity" and fits and case_key in fits:
        return fits[case_key]
    return defaults[powertrain]


def combined_power(powertrain: str, power_ice: float, power_ee: float, **kwargs) -> float:
    """Potencia combinada (kW) com os fatores efetivos do caso."""
    return effective_factors(powertrain, **kwargs).combine(power_ice, power_ee)
