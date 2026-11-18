"""Fixtures do B1 na base de referencia: itens de reposicao e rotas da BR23."""

from __future__ import annotations

import math
import os
import sqlite3

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    yield c
    c.close()


def test_intervalos_reproduzem_as_contagens_da_planilha(conn):
    """n = ceil(L / intervalo) - 1 com L = 200.000 km (so eventos antes de L)."""
    for idmi, intervalo, ref in conn.execute(
            "SELECT IDMI, IntervalKm, RefCount FROM P31_MaintenanceItem"):
        n = 0 if intervalo is None else math.ceil(200000 / intervalo) - 1
        assert n == ref, idmi


def test_so_a_bateria_de_tracao_e_a_auxiliar_tem_intervalo_digitado(conn):
    ids = {r[0] for r in conn.execute(
        "SELECT IDMI FROM P31_MaintenanceItem WHERE IntervalSource = 'Entered'")}
    assert ids == {"BATT_AUX", "BATT_TRAC"}
    inativos = {r[0] for r in conn.execute(
        "SELECT IDMI FROM P31_MaintenanceItem WHERE IntervalKm IS NULL")}
    assert inativos == {"FLD_78", "FLD_83"}


def test_jogo_de_pneus_tem_massa_e_composicao(conn):
    massa = conn.execute("SELECT MassPerUnitKg FROM P31_MaintenanceItem "
                         "WHERE IDMI='TIRE'").fetchone()[0]
    assert abs(massa - 9.0718474) < 1e-9
    soma = conn.execute("SELECT SUM(Share) FROM P31b_MaintenancePartShare "
                        "WHERE IDMI='TIRE'").fetchone()[0]
    assert abs(soma - 1) < 1e-12
    assert conn.execute("SELECT CorrectivePct FROM P32_CorrectiveMaintenance").fetchone()[0] == 0


def test_rotas_da_br23_cobrem_aco_ferro_e_aluminio(conn):
    assert [r[0] for r in conn.execute(
        "SELECT DISTINCT IDM FROM P61_BRRouteFactor ORDER BY IDM")] == ["1", "3", "4a", "4b"]
    assert conn.execute("SELECT COUNT(*) FROM P61_BRRouteFactor").fetchone()[0] == 16
    # cada material tem 4 rotas + 5 fracoes importadas
    for idm in ("1", "3", "4a", "4b"):
        assert conn.execute("SELECT COUNT(*) FROM P62_BRRouteShare WHERE IDM=?",
                            (idm,)).fetchone()[0] == 9


def test_fe_do_aco_por_rota_e_os_parametros_do_painel(conn):
    m, n = (conn.execute("SELECT EFRoute FROM P61_BRRouteFactor WHERE IDM='1' AND Route=?",
                         (r,)).fetchone()[0] for r in ("RECYCLED", "VIRGIN_MAIN"))
    assert abs(m - 0.826470588235294) < 1e-9 and abs(n - 3.52564705882353) < 1e-9
    assert conn.execute("SELECT LossNationalAdjIDCP FROM P61_BRRouteFactor "
                        "WHERE IDM='1' AND Route='GREEN'").fetchone()[0] == "X91"
    assert conn.execute("SELECT IDCP FROM P62_BRRouteShare WHERE IDM='1' AND "
                        "Route='VIRGIN_ALT'").fetchone()[0] == "X93"
