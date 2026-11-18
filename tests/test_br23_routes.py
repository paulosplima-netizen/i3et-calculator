"""Recomposicao da BR23 (T17): paridade com a lista digitada e variacao de parametros."""

from __future__ import annotations

import os
import sqlite3

import pytest

from core import br23_routes as br

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def tabelas(conn):
    return br.load_tables(conn)


def _digitado(conn, lista, idm):
    return conn.execute("SELECT EF FROM P11_EmissionFactor WHERE IDEFV=? AND IDM=?",
                        (lista, idm)).fetchone()[0]


def test_parametros_padrao_sao_os_do_i3et(tabelas):
    _, _, params = tabelas
    assert len(params) == 10
    assert params["X91"] == 0.15 and params["X92"] == 0.253 and params["X101"] == 0.3


def test_recomposicao_reproduz_a_lista_digitada(conn, tabelas):
    """I38: com os parametros do i3ET a BR23 recomposta e igual a digitada (1e-9)."""
    p61, p62, params = tabelas
    rec = br.recompose(p61, p62, params)
    for idm in ("1", "3", "4a", "4b"):
        assert rec[idm]["NATIONAL"] == pytest.approx(_digitado(conn, "BR23_100", idm), abs=1e-9)
        for tipo, (_imp, lista) in br.VEHICLE_TYPES.items():
            assert rec[idm][tipo] == pytest.approx(_digitado(conn, lista, idm), abs=1e-9), \
                (idm, tipo)


def test_valores_de_referencia_do_painel(tabelas):
    p61, p62, params = tabelas
    rec = br.recompose(p61, p62, params)
    assert rec["1"]["ICEV"] == pytest.approx(3.0331802352941177, abs=1e-9)      # Z11/Z96
    assert rec["1"]["ICEV_SUV"] == pytest.approx(3.103833941176, abs=1e-9)      # AA11
    assert rec["4a"]["ICEV"] == pytest.approx(8.375058496839161, abs=1e-9)      # Z18/Z102


def test_variar_cada_parametro_muda_so_os_materiais_que_o_leem(tabelas):
    p61, p62, params = tabelas
    base = br.recompose(p61, p62, params)
    leem = {"X91": {"1"}, "X92": {"1", "3"}, "X93": {"1", "3"}, "X94": {"1", "3"},
            "X95": {"1", "3"}, "X97": {"4a", "4b"}, "X98": {"4a", "4b"},
            "X99": {"4a", "4b"}, "X100": {"4a", "4b"}, "X101": {"4a"}}
    for chave, materiais in leem.items():
        alt = dict(params)
        alt[chave] = min(1.0, params[chave] + 0.05) if params[chave] < 0.95 else 0.5
        novo = br.recompose(p61, p62, alt)
        mudou = {idm for idm in base
                 if any(abs(novo[idm][t] - base[idm][t]) > 1e-12 for t in base[idm])}
        assert mudou == materiais, chave


def test_mais_aco_reciclado_reduz_o_fe_do_aco(tabelas):
    p61, p62, params = tabelas
    base = br.recompose(p61, p62, params)["1"]["NATIONAL"]
    alt = br.recompose(p61, p62, {**params, "X92": 0.5})["1"]["NATIONAL"]
    assert alt < base


def test_rota_recompoe_participacoes_que_somam_um(tabelas):
    _, p62, params = tabelas
    part = br.shares(p62, params)
    for idm in ("1", "3", "4a", "4b"):
        soma = sum(part[(idm, r)] for r in br.ROUTES)
        if idm == "3":                       # ferro fundido: 0,9 x aco nas demais rotas
            continue
        assert soma == pytest.approx(1.0, abs=1e-9), idm


def test_parametro_fora_de_zero_a_um_e_recusado(tabelas):
    p61, p62, params = tabelas
    with pytest.raises(ValueError):
        br.recompose(p61, p62, {**params, "X92": 1.2})


def test_avaliador_so_aceita_aritmetica():
    assert br.evaluate("(X92-0.1)/0.9", {"X92": 0.253}) == pytest.approx(0.17)
    with pytest.raises(ValueError):
        br.evaluate("__import__('os')", {})
