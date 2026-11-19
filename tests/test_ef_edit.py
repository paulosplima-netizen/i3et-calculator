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
    assert ef_edit.is_editable(c, base)          # Typed da base: editavel no projeto


def test_publicada_nao_e_editavel(conn):
    c, _ = conn
    base = _primeiro(c)
    c.execute("UPDATE P10_EFVersion SET Origin = 'Published' WHERE IDEFV = ?", (base,))
    assert not ef_edit.is_editable(c, base)
    with pytest.raises(ValueError, match="I48"):
        ef_edit.set_factor(c, base, "1", 1.0, reason="x")
    with pytest.raises(ValueError, match="I59"):
        ef_edit.set_factor(c, "NAO-EXISTE", "1", 1.0, reason="x")


def test_digitada_da_base_e_editavel_no_projeto(conn):
    c, path = conn
    base = _primeiro(c)
    assert ef_edit.origin(c, base) == "Typed" and ef_edit.is_editable(c, base)
    original = ef_edit.inherited_value(c, base, "1")
    antes = c.execute("SELECT EF FROM P11_EmissionFactor WHERE IDEFV = ? AND IDM = '1'",
                      (base,)).fetchone()[0]
    ef_edit.set_factor(c, base, "1", (original or 0) + 2.0, reason="erro de digitacao",
                       author="Paulo")
    c.commit()
    # a lista da base nao muda; o valor efetivo, sim, e so uma vez
    assert c.execute("SELECT EF FROM P11_EmissionFactor WHERE IDEFV = ? AND IDM = '1'",
                     (base,)).fetchone()[0] == antes
    eff = loader.effective_emission_factors(loader.load_sqlite(path))
    linha = eff[(eff["IDEFV"] == base) & (eff["IDM"] == "1")]
    assert len(linha) == 1 and linha["EF"].iloc[0] == pytest.approx((original or 0) + 2.0)
    visao = c.execute("SELECT EF FROM EF_Effective WHERE IDEFV = ? AND IDM = '1'",
                      (base,)).fetchall()
    assert [r[0] for r in visao] == [pytest.approx((original or 0) + 2.0)]
    st = ef_edit.status(c, base)
    assert st["changed"] == 1 and st["label"] == "Typed, altered"
    corr = ef_edit.corrections(c, base)
    assert list(corr["IDM"]) == ["1"] and corr["OriginalEF"].iloc[0] == pytest.approx(original)
    assert ef_edit.restore_factor(c, base, "1", reason="volta")
    assert ef_edit.status(c, base)["changed"] == 0


def test_copiar_publicada_para_digitada(conn):
    c, _ = conn
    base = _primeiro(c)
    c.execute("UPDATE P10_EFVersion SET Origin = 'Published' WHERE IDEFV = ?", (base,))
    with pytest.raises(ValueError, match="I49"):
        ef_edit.copy_to_typed(c, base, "COPIA", reason=" ")
    ef_edit.copy_to_typed(c, base, "COPIA", reason="corrigir o aco", author="Paulo")
    assert ef_edit.origin(c, "COPIA") == "Typed" and ef_edit.is_editable(c, "COPIA")
    st = ef_edit.status(c, "COPIA")
    assert st["derived_from"] == base and st["label"] == f"Typed, derived from {base}"
    ef_edit.set_factor(c, "COPIA", "1", 3.0, reason="corrigido", author="Paulo")
    assert ef_edit.status(c, "COPIA")["label"].endswith("altered")


def test_hash_dos_fatores_efetivos_i53(conn):
    c, _ = conn
    base = _primeiro(c)
    h0 = ef_edit.factors_hash(c, base)
    assert not ef_edit.needs_hash(c, base)               # lista da base intacta: ParamBaseHash
    ef_edit.set_factor(c, base, "1", 7.0, reason="teste")
    assert ef_edit.needs_hash(c, base) and ef_edit.factors_hash(c, base) != h0
    ef_edit.restore_factor(c, base, "1", reason="volta")
    assert ef_edit.factors_hash(c, base) == h0
    assert ef_edit.orphans(c) == []


def test_migracao_remove_a_chave_de_d05(conn):
    from core import schema
    c, _ = conn
    base = _primeiro(c)
    ef_edit.create_version(c, "MEU", "x", base, "f")
    ef_edit.set_factor(c, "MEU", "1", 4.0, reason="r", author="P")
    # volta ao desenho antigo (com a chave para D04) e migra de novo
    c.execute("DROP VIEW EF_Effective")
    c.execute("ALTER TABLE D05_UserEmissionFactor RENAME TO D05_new")
    c.execute("CREATE TABLE D05_UserEmissionFactor ("
              "IDM TEXT NOT NULL REFERENCES P09_Material(IDM), "
              "IDEFV TEXT NOT NULL REFERENCES D04_UserEFVersion(IDEFV), EF REAL NOT NULL, "
              "EFnotes TEXT, Author TEXT, ChangedAt TEXT, Reason TEXT, PRIMARY KEY (IDM, IDEFV))")
    c.execute("INSERT INTO D05_UserEmissionFactor SELECT * FROM D05_new")
    c.execute("DROP TABLE D05_new")
    c.execute(schema.DDL_VIEWS)
    assert any(r[2] == "D04_UserEFVersion"
               for r in c.execute("PRAGMA foreign_key_list(D05_UserEmissionFactor)"))
    assert schema.relax_d05(c) == ["D05_UserEmissionFactor: chave para D04 removida"]
    assert not any(r[2] == "D04_UserEFVersion"
                   for r in c.execute("PRAGMA foreign_key_list(D05_UserEmissionFactor)"))
    assert c.execute("SELECT EF, Author FROM D05_UserEmissionFactor WHERE IDEFV = 'MEU'"
                     ).fetchone() == (4.0, "P")
    assert schema.relax_d05(c) == []                        # idempotente
    ef_edit.set_factor(c, base, "2", 5.0, reason="lista da base agora aceita")


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
