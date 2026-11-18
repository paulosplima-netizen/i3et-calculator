"""Edicao de fatores de emissao (T15): regras I48 a I52 e efeito na rodada."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import ef_edit, loader

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture()
def conn(tmp_path):
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    c = sqlite3.connect(path)
    from core import project
    project.create(c, "EF")
    yield c, path
    c.close()


def _primeiro(c):
    return c.execute("SELECT IDEFV FROM P10_EFVersion ORDER BY IDEFV LIMIT 1").fetchone()[0]


def test_versao_exige_fonte_id_unico_e_origem(conn):
    c, _ = conn
    base = _primeiro(c)
    with pytest.raises(ValueError, match="fonte"):
        ef_edit.create_version(c, "MEU", "x", base, " ")
    with pytest.raises(ValueError, match="ja existe"):
        ef_edit.create_version(c, base, "x", base, "fonte")
    with pytest.raises(ValueError, match="origem"):
        ef_edit.create_version(c, "MEU", "x", "NAO-EXISTE", "fonte")
    ef_edit.create_version(c, "MEU", "x", base, "inventario do fornecedor")
    assert ef_edit.origin(c, "MEU") == "Own" and ef_edit.is_editable(c, "MEU")
    assert not ef_edit.is_editable(c, base)


def test_base_nao_e_editavel(conn):
    c, _ = conn
    with pytest.raises(ValueError, match="I48"):
        ef_edit.set_factor(c, _primeiro(c), "1", 1.0, reason="x")


def test_motivo_e_zero_explicito(conn):
    c, _ = conn
    base = _primeiro(c)
    ef_edit.create_version(c, "MEU", "x", base, "f")
    with pytest.raises(ValueError, match="I49"):
        ef_edit.set_factor(c, "MEU", "1", 2.0, reason="")
    with pytest.raises(ValueError, match="I50"):
        ef_edit.set_factor(c, "MEU", "1", 0.0, reason="medicao propria")
    ef_edit.set_factor(c, "MEU", "1", 0.0, reason="medicao propria", confirm_zero=True)


def test_editar_muda_o_fator_efetivo_e_restaurar_volta(conn):
    c, path = conn
    base = _primeiro(c)
    ef_edit.create_version(c, "MEU", "x", base, "f")
    c.commit()
    antes = loader.effective_emission_factors(loader.load_sqlite(path))
    v0 = antes[(antes["IDEFV"] == "MEU") & (antes["IDM"] == "1")]["EF"].iloc[0]
    ef_edit.set_factor(c, "MEU", "1", v0 + 1.0, reason="teste", author="Paulo")
    c.commit()
    dep = loader.effective_emission_factors(loader.load_sqlite(path))
    assert dep[(dep["IDEFV"] == "MEU") & (dep["IDM"] == "1")]["EF"].iloc[0] == \
        pytest.approx(v0 + 1.0)
    assert ef_edit.restore_factor(c, "MEU", "1", reason="volta", author="Paulo")
    c.commit()
    fim = loader.effective_emission_factors(loader.load_sqlite(path))
    assert fim[(fim["IDEFV"] == "MEU") & (fim["IDM"] == "1")]["EF"].iloc[0] == \
        pytest.approx(v0)
    acoes = [r[0] for r in c.execute("SELECT Action FROM D19_EFChangeLog ORDER BY IDLog")]
    assert acoes == ["override", "restore"]
    assert not ef_edit.restore_factor(c, "MEU", "1", reason="de novo")


def test_comparar_avisa_gwp_diferente(conn):
    c, path = conn
    base = loader.load_sqlite(path)
    eff = loader.effective_emission_factors(base)
    g = dict(zip(base["P10"]["IDEFV"], base["P10"]["GWPSet"]))
    ids = list(g)
    tabela, aviso = ef_edit.compare(eff, base["P09"], ids[0], ids[1], {**g, ids[1]: "OUTRO"})
    assert len(tabela) > 0 and aviso and "I52" in aviso
    _, sem = ef_edit.compare(eff, base["P09"], ids[0], ids[0], g)
    assert sem is None
