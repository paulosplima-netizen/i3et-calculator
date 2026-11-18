"""Telas do 0.11 (B1), abertas sem navegador sobre um projeto com uma rodada."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from tests.test_telas_010 import _abrir, projeto  # noqa: E402,F401


def test_t18_vida_do_veiculo_abre_e_soma_os_estagios(projeto):  # noqa: F811
    at = _abrir("T18_Vehicle_life", projeto)
    assert not at.exception, at.exception
    tabela = at.dataframe[0].value
    estagios = tabela[tabela["Stage"] != "Vehicle life, without use of energy"]
    total = tabela[tabela["Stage"] == "Vehicle life, without use of energy"]
    col = [c for c in tabela.columns if c.startswith("GHG")][0]
    assert abs(estagios[col].sum() - total[col].iloc[0]) < 0.2


def test_t18_sem_projeto_pede_para_abrir():
    at = _abrir("T18_Vehicle_life")
    assert not at.exception
    assert any("Home" in i.value or "Open or create" in i.value for i in at.info)
