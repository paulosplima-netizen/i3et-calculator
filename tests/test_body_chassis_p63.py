"""P63: massas de referencia de carroceria e chassi por receita (T38, bloco B1)."""

import csv
import os
import sqlite3

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(REPO, "data", "csv", "fase_b", "P63_RecipeBodyChassisMass.csv")
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def linhas():
    with open(CSV, encoding="utf-8-sig", newline="") as fh:
        return {r["IDVMR"]: r for r in csv.DictReader(fh, delimiter=";")}


def test_uma_linha_por_receita(linhas):
    conn = sqlite3.connect(DB)
    receitas = {r[0] for r in conn.execute("SELECT IDVMR FROM P15_VehicleMaterialRecipe")}
    assert len(linhas) == 68
    assert set(linhas) == receitas


def test_razao_e_parcela_coerentes(linhas):
    for idvmr, r in linhas.items():
        a, b = float(r["BodyMassRefKg"]), float(r["ChassisMassRefKg"])
        k, s = float(r["ChassisBodyRatio"]), float(r["BodyShareOfMassAdj"])
        assert a > 0 and b > 0, idvmr
        assert k == pytest.approx(b / a, rel=1e-9), idvmr          # linha 627 = linha 55 / linha 54
        assert 0 < s < 1, idvmr                                     # I45
        assert s == pytest.approx(1 / (1 + k), rel=1e-9), idvmr


def test_categorias_com_chassi_mais_pesado(linhas):
    acima = {i for i, r in linhas.items() if float(r["ChassisBodyRatio"]) > 1}
    assert acima == {"FCV-P25", "HEV-P27", "PHEV-P28", "BEV-P29", "FCV-P30", "PHEV-S28"}
    assert all(float(linhas[i]["BodyShareOfMassAdj"]) < 0.5 for i in acima)


def test_veiculos_de_escolha_livre_sv1_a_sv4(linhas):
    esperado = {"ICEV-G21": 0.4801512287334592, "HEV-G22": 0.4929019363360543,
                "PHEV-G23": 0.48015122873345956, "BEV-G24": 0.4929019363360541}
    for idvmr, k in esperado.items():
        assert float(linhas[idvmr]["ChassisBodyRatio"]) == pytest.approx(k, rel=1e-12)
    assert float(linhas["ICEV-G21"]["BodyMassRefKg"]) == pytest.approx(746.7680026958842)
    assert float(linhas["ICEV-G21"]["ChassisMassRefKg"]) == pytest.approx(358.56157407326)
