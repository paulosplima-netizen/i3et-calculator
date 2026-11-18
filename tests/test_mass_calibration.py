"""Calibracao de massa (T38): repartidora s, regras I40/I44/I45 e metodo da planilha."""

from __future__ import annotations

import json
import os

import pandas as pd
import pytest

from core import mass_calibration as mc

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(REPO, "tests", "fixtures", "b1_reference.json")


def _c02(a=600.0, b=250.0):
    return pd.DataFrame({"IDGG": ["A", "B", "D", "K"], "MassIDGG": [a, b, 200.0, 40.0]})


def test_diferenca_zero_nao_muda_nada():
    out = mc.apply_to_c02(_c02(), 0.0, 0.7)
    assert (out["CalibrationKg"] == 0).all()
    assert (out["MassIDGG"] == _c02()["MassIDGG"]).all()
    assert (out["FinalMassKg"] == out["EstimatedMassKg"]).all()


@pytest.mark.parametrize("adj,s", [(30.0, 0.7), (-30.0, 0.7), (30.0, 0.0), (30.0, 1.0),
                                   (-100.0, 0.5)])
def test_reparticao_so_em_carroceria_e_chassi(adj, s):
    base = _c02()
    out = mc.apply_to_c02(base, adj, s).set_index("IDGG")
    assert out.loc["A", "CalibrationKg"] == pytest.approx(s * adj)
    assert out.loc["B", "CalibrationKg"] == pytest.approx((1 - s) * adj)
    assert out.loc["D", "CalibrationKg"] == 0 and out.loc["K", "CalibrationKg"] == 0
    assert out["CalibrationKg"].sum() == pytest.approx(adj)                      # I44
    assert out["FinalMassKg"].sum() == pytest.approx(base["MassIDGG"].sum() + adj)


def test_massa_final_igual_a_declarada_no_botao():
    base = _c02()
    declarada = 1130.0
    adj = mc.adjustment_from_declared(declarada, base["MassIDGG"].sum())
    out = mc.apply_to_c02(base, adj, 0.67)
    assert out["MassIDGG"].sum() == pytest.approx(declarada)
    row = mc.validation_row(out, declared_kg=declarada, adjustment_kg=adj, s=0.67)
    assert row["ResidualKg"] == pytest.approx(0, abs=1e-9)
    assert row["BodyChassisMassAfter"] - row["BodyChassisMassBefore"] == pytest.approx(adj)


@pytest.mark.parametrize("s", [-0.01, 1.01])
def test_parcela_fora_de_zero_a_um_e_recusada(s):
    with pytest.raises(ValueError):
        mc.apply_to_c02(_c02(), 10.0, s)


def test_massa_negativa_e_recusada():
    with pytest.raises(ValueError):
        mc.apply_to_c02(_c02(a=20.0), -100.0, 0.9)         # A ficaria negativa (I40)


def test_sem_carroceria_ou_chassi_nao_ha_onde_alocar():
    sem = pd.DataFrame({"IDGG": ["D"], "MassIDGG": [200.0]})
    with pytest.raises(ValueError):
        mc.apply_to_c02(sem, 5.0, 0.5)


# --------------------------------------------------------------------------
# Metodo da planilha (P69 = "Sim"): paridade com FD628 e FD629 (SV1 a SV4)
# --------------------------------------------------------------------------
def test_metodo_da_planilha_reproduz_a_b_das_sv1_a_sv4():
    with open(REF, encoding="utf-8") as fh:
        ref = json.load(fh)
    for col, m in ref["mass_calibration"].items():
        r = ref["m2_columns"][col]["rows"]
        outros = sum(r[str(i)] for i in range(72, 82))
        a, b = mc.sheet_method(m["declared_row35"], outros, m["k"])
        assert a == pytest.approx(m["A_sheet"], rel=1e-9), col
        assert b == pytest.approx(m["B_sheet"], rel=1e-9), col


def test_metodo_da_planilha_transfere_massa_mesmo_sem_diferenca():
    """B1-DIV-01: com declarada = calculada, a planilha move massa de A para B."""
    with open(REF, encoding="utf-8") as fh:
        ref = json.load(fh)
    esperado = {"FD": 54.2, "FE": 40.9, "FF": 1.7, "FG": 49.4}
    for col, m in ref["mass_calibration"].items():
        r = ref["m2_columns"][col]["rows"]
        outros = sum(r[str(i)] for i in range(72, 82))
        t = mc.sheet_method_transfer(m["A_est"], m["B_est"], m["declared_row35"], outros, m["k"])
        assert t == pytest.approx(esperado[col], abs=0.05), col
        # o metodo do aplicativo, com a mesma entrada, nao transfere nada
        c02 = pd.DataFrame({"IDGG": ["A", "B"], "MassIDGG": [m["A_est"], m["B_est"]]})
        out = mc.apply_to_c02(c02, 0.0, 1 / (1 + m["k"]))
        assert (out["CalibrationKg"] == 0).all()


# --------------------------------------------------------------------------
# Integracao com o calculo
# --------------------------------------------------------------------------
def _um_veiculo(base, **extra):
    from core import calc
    cen = base["D02"].iloc[0]
    idv = int(cen["IDV"])
    rows = base["D03"][base["D03"]["IDV"] == idv]
    gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
    supplied = {int(r["IDVP"]) for _, r in rows.iterrows() if not int(r["IsCalculated"] or 0)}
    hit = rows[rows["IDVP"] == 32]
    bid = hit.iloc[0]["GCText"] if len(hit) else None
    veic = base["D01"].set_index("IDV").loc[idv]
    return calc.calculate_vehicle(
        base, gc, powertrain=veic["IDVPT"], battery_id=bid, idmpv=int(cen["IDMPV"]),
        idvmr=cen["IDVMR"], idefv=cen["IDEFV"], idapv=cen["IDAPV"],
        boundary=cen["Boundary"], supplied=supplied, **extra)


def test_calculo_com_calibracao_soma_a_diferenca_a_massa_do_veiculo(base):
    zero = _um_veiculo(base)
    cal = _um_veiculo(base, mass_adjustment_kg=25.0, body_share=0.6)
    assert cal["totals"]["MassIDV"] == pytest.approx(zero["totals"]["MassIDV"] + 25.0)
    c02 = cal["C02"].set_index("IDGG")
    assert c02.loc["A", "CalibrationKg"] == pytest.approx(15.0)
    assert c02.loc["B", "CalibrationKg"] == pytest.approx(10.0)
    outros = c02.drop(["A", "B"])
    assert (outros["CalibrationKg"] == 0).all()
    # com diferenca zero o resultado e identico ao de antes
    ident = _um_veiculo(base, mass_adjustment_kg=0.0, body_share=0.3)
    assert ident["totals"]["MassIDV"] == zero["totals"]["MassIDV"]
    assert ident["totals"]["GHGCradleToGate"] == zero["totals"]["GHGCradleToGate"]
