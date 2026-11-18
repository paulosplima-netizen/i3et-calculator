"""`tools/build_review_data.py`: dados dos prototipos de tela a partir da base (B0, item 8)."""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import build_review_data as brd  # noqa: E402

BASE = os.path.join(REPO, "data", "base_referencia.sqlite")
#: Arquivo do pacote "Interfaces Revisadas": fica fora do repositorio.
PROTOTIPO = os.environ.get("I3ET_REVIEW_DATA", os.path.expanduser(
    "~/mnt/Documentação/Interfaces Revisadas para o i3ET_T01-T46_20261116/model-data.js"))


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{BASE}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_secoes_derivadas_tem_o_tamanho_da_base(conn):
    d = brd.derived(conn)
    assert len(d[("panel", "params")]) == 205
    assert len(d[("panel", "out")]) == 47
    assert len(d[("market", "params")]) == 58
    assert len(d[("market", "vehicles")]) == 154
    assert len(d[("market", "pbev")]) == 843
    assert d[("market", "const", "kw_to_hp")] == pytest.approx(1.34102)


def test_gravacao_e_leitura_dao_o_mesmo_objeto(conn, tmp_path):
    esqueleto = {"panel": {"params": [], "out": []},
                 "market": {"params": [], "vehicles": [], "pbev": [], "const": {}}}
    data = brd.build(conn, esqueleto)
    caminho = str(tmp_path / "model-data.js")
    brd.write_js(data, caminho)
    assert open(caminho, encoding="utf-8").read().startswith("window.i3etData=")
    assert brd.read_js(caminho) == data


@pytest.mark.skipif(not os.path.exists(PROTOTIPO), reason="pacote de prototipos ausente")
def test_numeros_do_prototipo_batem_com_a_base(conn):
    """O que a base nao guarda: 3 textos de 'mais frequente' do painel e a unidade do O44."""
    resultado = brd.compare(conn, brd.read_js(PROTOTIPO))
    toleradas = {"panel.params": 3, "panel.out": 1}
    for nome, (diferentes, _) in resultado.items():
        assert diferentes <= toleradas.get(nome, 0), (nome, diferentes)
