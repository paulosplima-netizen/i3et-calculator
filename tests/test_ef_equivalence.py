"""Fatores de uma versao do GREET aplicados a receita de outra (core/ef_equivalence.py)."""

from __future__ import annotations

import pandas as pd
import pytest

from core import calc, ef_equivalence
from core.log import Log

from test_edge_cases import _project_vehicle

G22_FORJADO = 15.740704098789761      # IDM 4, celula AE9 da guia de fatores do i3ET
G23_CHAPA, G23_EXTRUDADO = 11.938201027272028, 4.7703153112467085


def _ef(**por_versao):
    linhas = []
    for idefv, fatores in por_versao.items():
        for idm, valor in fatores.items():
            linhas.append({"IDM": idm, "IDEFV": idefv, "EF": valor, "EFnotes": "t",
                           "IsUserDefined": 0})
    return pd.DataFrame(linhas)


def _fator(tabela, idefv, idm):
    hit = tabela[(tabela["IDEFV"] == idefv) & (tabela["IDM"] == idm)]
    return hit.iloc[0]["EF"] if len(hit) else None


# --- a base ---------------------------------------------------------------

def test_g22_tem_so_o_aluminio_unico(base):
    p11 = base["P11"].set_index(["IDM", "IDEFV"])["EF"]
    assert p11[("4", "G22")] == pytest.approx(G22_FORJADO, abs=1e-9)
    assert pd.isna(p11[("4a", "G22")]) and pd.isna(p11[("4b", "G22")])
    assert p11[("4a", "G23")] == pytest.approx(G23_CHAPA, abs=1e-9)
    assert p11[("4b", "G23")] == pytest.approx(G23_EXTRUDADO, abs=1e-9)


def test_p57_pesos_somam_um_e_vem_das_receitas(base):
    p57 = base["P57"]
    assert set(p57["IDMChild"]) == {"4a", "4b"} and set(p57["IDMParent"]) == {"4"}
    assert p57["Weight"].sum() == pytest.approx(1.0, abs=1e-12)
    p16, p15 = base["P16"], base["P15"]
    # as 30 receitas do GREET 2024 que a base calcula (sem FCEV): ICEV-G21, HEV-G22...
    familia = list(p15[p15["DsVMR"].str.contains("GREET 2024", na=False)
                       & (p15["IDVPT"] != "FCEV")]["IDVMR"])
    assert len(familia) == 30
    soma = p16[p16["IDVMR"].isin(familia)].groupby("IDM")["MshareGG"].sum()
    esperado = soma["4a"] / (soma["4a"] + soma["4b"])
    peso = p57.set_index("IDMChild")["Weight"]
    assert peso["4a"] == pytest.approx(esperado, abs=1e-9)


# --- caso 1: receita nos tipos novos, lista no tipo unico ------------------

def test_receita_nova_com_lista_antiga_usa_o_fator_unico_nos_dois_tipos(base):
    ef = _ef(G22={"4": G22_FORJADO, "4a": None, "4b": None})
    log = Log()
    saida, alertas = ef_equivalence.adapt(ef, "G22", {"4a", "4b", "1"}, base["P57"], log=log)
    assert _fator(saida, "G22", "4a") == pytest.approx(G22_FORJADO)
    assert _fator(saida, "G22", "4b") == pytest.approx(G22_FORJADO)
    assert saida.set_index("IDM").loc[["4a", "4b"], "IsAdapted"].tolist() == [1, 1]
    assert {a["kind"] for a in alertas} == {"ParentToChild"} and len(alertas) == 2
    assert [e.rule for e in log.of("AVISO")] == ["I28", "I28"]


def test_so_o_tipo_usado_e_adaptado(base):
    ef = _ef(G22={"4": G22_FORJADO, "4a": None, "4b": None})
    saida, alertas = ef_equivalence.adapt(ef, "G22", {"4a"}, base["P57"])
    assert _fator(saida, "G22", "4a") == pytest.approx(G22_FORJADO)
    assert pd.isna(_fator(saida, "G22", "4b")) and len(alertas) == 1


# --- caso 2: receita no tipo unico, lista nos tipos novos -------------------

def test_receita_antiga_com_lista_nova_usa_a_media_ponderada(base):
    ef = _ef(G23={"4": None, "4a": G23_CHAPA, "4b": G23_EXTRUDADO})
    log = Log()
    saida, alertas = ef_equivalence.adapt(ef, "G23", {"4"}, base["P57"], log=log)
    w = base["P57"].set_index("IDMChild")["Weight"]
    esperado = w["4a"] * G23_CHAPA + w["4b"] * G23_EXTRUDADO
    assert _fator(saida, "G23", "4") == pytest.approx(esperado)
    assert G23_EXTRUDADO < esperado < G23_CHAPA
    assert [a["kind"] for a in alertas] == ["ChildrenToParent"]
    assert len(log.of("AVISO")) == 1


def test_o_peso_e_parametro_e_muda_o_resultado(base):
    ef = _ef(G23={"4": None, "4a": G23_CHAPA, "4b": G23_EXTRUDADO})
    p57 = base["P57"].copy()
    p57["Weight"] = [0.5, 0.5]
    saida, _ = ef_equivalence.adapt(ef, "G23", {"4"}, p57)
    assert _fator(saida, "G23", "4") == pytest.approx((G23_CHAPA + G23_EXTRUDADO) / 2)


# --- o que nao muda ------------------------------------------------------------

def test_versoes_que_combinam_nao_geram_alerta(base):
    ef = _ef(G23={"4": None, "4a": G23_CHAPA, "4b": G23_EXTRUDADO})
    saida, alertas = ef_equivalence.adapt(ef, "G23", {"4a", "4b"}, base["P57"])
    assert alertas == [] and (saida["IsAdapted"] == 0).all()


def test_sem_fator_em_nenhum_dos_lados_continua_ausente(base):
    ef = _ef(X={"4": None, "4a": None, "4b": None})
    saida, alertas = ef_equivalence.adapt(ef, "X", {"4", "4a", "4b"}, base["P57"])
    assert alertas == [] and saida["EF"].isna().all()


def test_so_um_filho_com_fator_nao_forma_media(base):
    ef = _ef(X={"4": None, "4a": 10.0, "4b": None})
    saida, alertas = ef_equivalence.adapt(ef, "X", {"4"}, base["P57"])
    assert alertas == [] and pd.isna(_fator(saida, "X", "4"))


def test_a_tabela_de_entrada_nao_e_alterada(base):
    ef = _ef(G22={"4": G22_FORJADO, "4a": None, "4b": None})
    antes = ef.copy()
    ef_equivalence.adapt(ef, "G22", {"4a", "4b"}, base["P57"])
    pd.testing.assert_frame_equal(ef, antes)


def test_sem_p57_nao_adapta():
    ef = _ef(G22={"4": G22_FORJADO, "4a": None, "4b": None})
    saida, alertas = ef_equivalence.adapt(ef, "G22", {"4a"}, None)
    assert alertas == [] and pd.isna(_fator(saida, "G22", "4a"))


# --- no calculo ------------------------------------------------------------------

def test_o_calculo_avisa_e_usa_o_fator_adaptado(base):
    args = _project_vehicle(base)
    assert args["idefv"] == "G22"                    # BP01 usa a lista G22 e uma receita BISD
    r = calc.calculate_vehicle(base, **args)
    c03 = r["C03"]
    chapa = c03[c03["IDM"] == "4a"]
    assert len(chapa) and chapa["EF"].tolist() == pytest.approx([G22_FORJADO] * len(chapa))
    assert chapa["HasFactor"].eq(1).all()
    assert any(a["kind"] == "ParentToChild" for a in r["ef_alerts"])
    assert any(e.rule == "I28" for e in r["log"].of("AVISO"))


def test_com_a_lista_g23_nao_ha_alerta_e_o_fator_e_o_do_tipo(base):
    args = {**_project_vehicle(base), "idefv": "G23"}
    r = calc.calculate_vehicle(base, **args)
    chapa = r["C03"][r["C03"]["IDM"] == "4a"]
    assert len(chapa) and chapa["EF"].tolist() == pytest.approx([G23_CHAPA] * len(chapa))
    assert r["ef_alerts"] == []
