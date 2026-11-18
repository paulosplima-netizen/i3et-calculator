"""Fim de vida do veiculo (T17; M2 T509).

Bloco B1. Sem Streamlit. Tres metodos, so o escolhido contribui (I36):

    GLIDER_BATTERY     fator do veiculo sem bateria x massa do glider
                       + fator da bateria x kWh da bateria (padrao, decisao 10;
                       fatores do painel: X76 = 0,2 kg CO2e/kg, X77 = 20 kg CO2e/kWh)
    AGGREGATE_VEHICLE  fator unico por veiculo (IDM 100 da lista; reproduz T509)
    EXCLUDED           nao conta

Massa do glider = massa do veiculo sem baterias e sem fluidos (M2 linha 662). Os fatores de todos
os metodos ficam no resultado (C16) mesmo quando nao somam.
"""

from __future__ import annotations

METHODS = ("GLIDER_BATTERY", "AGGREGATE_VEHICLE", "EXCLUDED")


def glider_mass(vehicle_mass_kg: float, *, aux_battery_kg: float = 0.0,
                traction_battery_kg: float = 0.0, fluids_kg: float = 0.0) -> float:
    """Massa do glider: o veiculo sem baterias (Iaux, Iprinc) e sem fluidos (K).

    E a linha 662 do M2 ("Car without Batteries and Fluids"); nunca negativa.
    """
    return max(0.0, float(vehicle_mass_kg) - aux_battery_kg - traction_battery_kg - fluids_kg)


def end_of_life(method: str, *, glider_mass_kg: float, battery_kwh: float,
                factor_glider: float, factor_battery: float,
                factor_vehicle: float | None) -> dict:
    """Linha de C16: o GHG do fim de vida pelo metodo escolhido e os tres fatores."""
    if method not in METHODS:
        raise ValueError(f"metodo de fim de vida invalido: {method!r}")
    if glider_mass_kg < 0 or battery_kwh < 0:
        raise ValueError("massa do glider e capacidade da bateria nao podem ser negativas")
    if method == "GLIDER_BATTERY":
        ghg = factor_glider * glider_mass_kg + factor_battery * battery_kwh
    elif method == "AGGREGATE_VEHICLE":
        if factor_vehicle is None:
            raise ValueError("a lista de fatores nao tem o fator por veiculo (IDM 100)")
        ghg = float(factor_vehicle)
    else:
        ghg = 0.0
    return {"EoLMethod": method, "GliderMassKg": glider_mass_kg, "BatteryKWh": battery_kwh,
            "FactorGlider": factor_glider, "FactorBattery": factor_battery,
            "FactorVehicle": factor_vehicle, "GHGEoL": ghg}
