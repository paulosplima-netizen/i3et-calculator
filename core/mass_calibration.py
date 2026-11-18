"""Calibracao da massa pela massa declarada (T38, "Calibrate to declared mass").

Bloco B1. Sem Streamlit. A massa projetada pelos parametros do manual e pelos
betas e imprecisa; a massa total do manual e mais confiavel. A diferenca
(declarada - calculada), positiva ou negativa, vai para a carroceria (A) e o
chassi (B), os grupos sujeitos a personalizacao:

    A_final = A_est + s . Adj
    B_final = B_est + (1 - s) . Adj          0 <= s <= 1 (I45)

Os outros grupos nao mudam. Com Adj = 0 nada muda. s e fixo por receita (P63),
s = A / (A + B) = 1 / (1 + k), e pode ser editado pelo usuario.

O metodo da planilha (M2 P69 = "Sim") e diferente: A = (declarada - soma dos
demais grupos) / (1 + k) e B = k . A. Ele transfere massa entre A e B mesmo sem
diferenca (divergencia B1-DIV-01) e so existe aqui para paridade.

Blocos:
    MC1  repartidora e regras
    MC2  aplicacao ao C02
    MC3  linha de validacao (C34)
    MC4  metodo da planilha (paridade)
"""

from __future__ import annotations

import pandas as pd

BODY, CHASSIS = "A", "B"
BODY_CHASSIS = (BODY, CHASSIS)
TOL = 1e-9


# --------------------------------------------------------------------------
# BLOCO MC1 -- repartidora
# --------------------------------------------------------------------------
def adjustment_from_declared(declared_kg: float, calculated_kg: float) -> float:
    """Adj = declarada - calculada (com sinal)."""
    return float(declared_kg) - float(calculated_kg)


def check_share(s: float) -> None:
    """I45: a parcela da carroceria fica entre 0 e 1."""
    if not 0.0 <= s <= 1.0:
        raise ValueError(f"parcela da carroceria s = {s} fora de [0, 1]")


def distribute(body_est_kg: float, chassis_est_kg: float, adjustment_kg: float,
               s: float) -> tuple[float, float]:
    """(A_final, B_final). I40: nenhuma das duas fica negativa."""
    check_share(s)
    a = body_est_kg + s * adjustment_kg
    b = chassis_est_kg + (1.0 - s) * adjustment_kg
    if a < -TOL or b < -TOL:
        raise ValueError(
            f"a calibracao de {adjustment_kg:.1f} kg deixaria carroceria ({a:.1f} kg) "
            f"ou chassi ({b:.1f} kg) negativos")
    return max(a, 0.0), max(b, 0.0)


# --------------------------------------------------------------------------
# BLOCO MC2 -- C02
#   Le      : C02 (IDGG, MassIDGG, ...), a diferenca e s.
#   Devolve : C02 com EstimatedMassKg, CalibrationKg, FinalMassKg; MassIDGG passa
#             a ser a massa final.
# --------------------------------------------------------------------------
def apply_to_c02(c02: pd.DataFrame, adjustment_kg: float, s: float) -> pd.DataFrame:
    out = c02.copy()
    est = out["MassIDGG"].astype(float)
    out["EstimatedMassKg"] = est
    out["CalibrationKg"] = 0.0
    if abs(adjustment_kg) > 0:
        check_share(s)
        for grupo in (BODY, CHASSIS):
            if grupo not in set(out["IDGG"]):
                raise ValueError(f"C02 sem o grupo {grupo}: nao ha onde alocar a diferenca")
        a = float(est[out["IDGG"] == BODY].iloc[0])
        b = float(est[out["IDGG"] == CHASSIS].iloc[0])
        a_final, b_final = distribute(a, b, adjustment_kg, s)
        out.loc[out["IDGG"] == BODY, "CalibrationKg"] = a_final - a
        out.loc[out["IDGG"] == CHASSIS, "CalibrationKg"] = b_final - b
    out["FinalMassKg"] = out["EstimatedMassKg"] + out["CalibrationKg"]
    out["MassIDGG"] = out["FinalMassKg"]
    # I44
    if abs(out["CalibrationKg"].sum() - adjustment_kg) > 1e-6:
        raise ValueError("a soma da calibracao nao e igual a diferenca (I44)")
    return out


# --------------------------------------------------------------------------
# BLOCO MC3 -- C34
# --------------------------------------------------------------------------
def validation_row(c02_calibrated: pd.DataFrame, *, declared_kg: float | None,
                   adjustment_kg: float, s: float | None, mass_basis: str = "",
                   declared_source: str = "") -> dict:
    est = float(c02_calibrated["EstimatedMassKg"].sum())
    final = float(c02_calibrated["FinalMassKg"].sum())
    ab = c02_calibrated["IDGG"].isin([BODY, CHASSIS])
    diff = None if declared_kg is None else declared_kg - est
    return {
        "MassBasis": mass_basis, "DeclaredMassKg": declared_kg, "CalculatedMassKg": est,
        "DiffKg": diff,
        "DiffPct": None if diff is None or not est else 100.0 * diff / est,
        "AdjustmentKg": adjustment_kg,
        "ResidualKg": None if declared_kg is None else declared_kg - final,
        "DeclaredSource": declared_source, "BodyShare": s,
        "BodyChassisMassBefore": float(c02_calibrated.loc[ab, "EstimatedMassKg"].sum()),
        "BodyChassisMassAfter": float(c02_calibrated.loc[ab, "FinalMassKg"].sum()),
    }


# --------------------------------------------------------------------------
# BLOCO MC4 -- metodo da planilha (paridade; B1-DIV-01)
# --------------------------------------------------------------------------
def sheet_method(declared_kg: float, other_groups_kg: float, k: float) -> tuple[float, float]:
    """(A, B) do M2 com P69 = "Sim": A = (declarada - demais) / (1 + k), B = k . A."""
    a = (declared_kg - other_groups_kg) / (1.0 + k)
    return a, k * a


def sheet_method_transfer(a_est: float, b_est: float, declared_kg: float,
                          other_groups_kg: float, k: float) -> float:
    """Massa que o metodo da planilha tira de A e poe em B (negativa se for o contrario)."""
    a, _b = sheet_method(declared_kg, other_groups_kg, k)
    return a_est - a
