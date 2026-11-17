"""Regras de valor padrao (core/vehicle_defaults.py) contra o levantamento de 10/11."""

from __future__ import annotations

import os
import sqlite3

import pytest

from core import vehicle_defaults as vd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{BASE}?mode=ro", uri=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def cmp(conn):
    return vd.compare(conn, hp_per_kw=vd.HP_PER_KW)


def test_contagens_de_divergencia_iguais_as_do_levantamento(cmp):
    assert cmp[17]["differ"] == 34      # ar-condicionado
    assert cmp[22]["differ"] == 34      # instrumentacao
    assert cmp[44]["differ"] == 19      # porte
    assert cmp[18]["differ"] == 0       # partida: o fator e igual nas tres faixas
    assert cmp[4]["differ"] == 0        # bateria de utilidades


def test_vidros_sem_regra_para_van_e_chassis(cmp):
    assert cmp[13]["no_rule"] == 25 and cmp[13]["differ"] == 0


def test_primeira_regra_que_atende_vale(conn):
    rules = vd.load_rules(conn)
    luxo = {"IDVPT": "ICEV", "IDVDT": "Sedan", "IDVS": "Subcompact", "IDLR": "Luxury",
            "params": {}}
    assert vd.default_value(rules, luxo, 17, hp_per_kw=vd.HP_PER_KW) == 20000.0
    luxo["IDLR"] = "Regular"
    assert vd.default_value(rules, luxo, 17, hp_per_kw=vd.HP_PER_KW) == 14000.0


def test_partida_e_fator_da_potencia_e_bev_vale_zero(conn):
    rules = vd.load_rules(conn)
    base = {"IDVDT": "Sedan", "IDVS": "Compact", "IDLR": "Regular"}
    ice = {**base, "IDVPT": "ICEV", "params": {vd.IDMP_POWER_ICE: 100.0}}
    assert vd.default_value(rules, ice, 18, hp_per_kw=vd.HP_PER_KW) == pytest.approx(0.03 * 100.0)
    bev = {**base, "IDVPT": "BEV", "params": {}}
    assert vd.default_value(rules, bev, 18, hp_per_kw=vd.HP_PER_KW) == 0.0


def test_faixa_de_potencia_usa_o_fator_recebido(conn):
    rules = vd.load_rules(conn)
    v = {"IDVPT": "ICEV", "IDVDT": "Sedan", "IDVS": "Compact", "IDLR": "Regular",
         "params": {vd.IDMP_POWER_ICE: 100.0}}               # 134 hp
    assert vd.default_value(rules, v, 4, hp_per_kw=vd.HP_PER_KW) == 0.72
    assert vd.default_value(rules, v, 4, hp_per_kw=0.5) == 0.6   # 50 hp
