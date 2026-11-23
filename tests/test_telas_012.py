"""Telas do B2 (T39, T40, T42): so o usuario master as ve; abertas sem navegador."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from tests.test_telas_010 import _abrir  # noqa: E402

TELAS = ["T39_PBEV_import", "T40_FENABRAVE_import", "T42_Weighted_references"]


@pytest.mark.parametrize("tela", TELAS)
def test_sem_senha_configurada_a_tela_explica_e_nao_mostra_dados(tela, monkeypatch):
    monkeypatch.delenv("I3ET_MASTER_PASSWORD", raising=False)
    at = _abrir(tela)
    assert not at.exception, at.exception
    assert any("master user only" in i.value for i in at.info)
    assert len(at.dataframe) == 0 and len(at.metric) == 0


@pytest.mark.parametrize("tela", TELAS)
def test_com_senha_so_o_master_ve_as_tabelas(tela, monkeypatch):
    monkeypatch.setenv("I3ET_MASTER_PASSWORD", "segredo")
    at = _abrir(tela)
    assert not at.exception, at.exception
    assert len(at.dataframe) == 0                                  # ainda sem acesso
    at.text_input(key="master_pwd").set_value("errada").run()
    assert any("Wrong password" in e.value for e in at.error) and len(at.dataframe) == 0
    at.text_input(key="master_pwd").set_value("segredo").run()
    assert not at.exception, at.exception
    assert len(at.dataframe) > 0


def test_t39_mostra_a_edicao_e_o_vinculo(monkeypatch):
    monkeypatch.setenv("I3ET_MASTER_PASSWORD", "x")
    at = _abrir("T39_PBEV_import", master_ok=True)
    assert not at.exception, at.exception
    ed = at.dataframe[0].value
    assert ed["Edition"].tolist() == ["PBEV2026"] and int(ed["Records"].iloc[0]) == 843
    assert any("market vehicles are linked" in c.value for c in at.caption)


def test_t40_lista_os_111_modelos_e_os_ajustados(monkeypatch):
    monkeypatch.setenv("I3ET_MASTER_PASSWORD", "x")
    at = _abrir("T40_FENABRAVE_import", master_ok=True)
    assert not at.exception, at.exception
    assert len(at.dataframe[1].value) == 111
    ajustados = at.dataframe[2].value
    assert 0 < len(ajustados) < 20
    assert (ajustados["Units (source)"] != ajustados["Units (adopted)"]).all()


def test_t42_recalcula_igual_ao_modelo_e_mostra_a_cobertura(monkeypatch):
    monkeypatch.setenv("I3ET_MASTER_PASSWORD", "x")
    at = _abrir("T42_Weighted_references", master_ok=True)
    assert not at.exception, at.exception
    valores = {m.label: m.value for m in at.metric}
    assert valores["Market total, 2025 (FENABRAVE)"] == "2,549,462"
    assert valores["Top 50 + top 50 (FENABRAVE)"] == "2,424,281"
    assert valores["Segments / market"] == "78.8%"
    quadro = next(d.value for d in at.dataframe if "Group" in d.value.columns)
    assert int(quadro["Total"].sum()) == 2424281
    pesos = next(d.value for d in at.dataframe if "Difference" in d.value.columns)
    assert pesos["Difference"].abs().max() < 1e-6
    categoria = next(b for b in at.selectbox if b.label == "Category")
    categoria.select("A4 · PUT Large Regular").run()
    assert not at.exception, at.exception
    pesos = next(d.value for d in at.dataframe if "Difference" in d.value.columns)
    assert pesos["Difference"].abs().max() < 1e-6
