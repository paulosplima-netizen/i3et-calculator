"""Painel de parametros: fixtures P64/P65 e nucleo (core/param_review.py)."""

from __future__ import annotations

import os
import sqlite3

import pytest

from core import param_review as pr

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture(scope="module")
def ref():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    yield c
    c.close()


@pytest.fixture()
def mem(ref):
    c = sqlite3.connect(":memory:")
    ref.backup(c)
    yield c
    c.close()


# --------------------------------------------------------------------------
# Fixtures na base
# --------------------------------------------------------------------------
def test_fixture_tem_120_parametros_e_260_fontes(ref):
    assert ref.execute("SELECT COUNT(*) FROM P64_ParamRevision").fetchone()[0] == 120
    assert ref.execute("SELECT COUNT(*) FROM P65_ParamRevisionSource").fetchone()[0] == 260


def test_contagens_do_artefato(ref):
    por_acao = dict(ref.execute("SELECT Action, COUNT(*) FROM P64_ParamRevision GROUP BY 1"))
    assert por_acao == {"keep": 106, "adjust": 9, "verify": 5}
    assert ref.execute("SELECT SUM(Spotlight) FROM P64_ParamRevision").fetchone()[0] == 17
    assert ref.execute("SELECT SUM(Accepted) FROM P64_ParamRevision").fetchone()[0] == 11
    assert ref.execute("SELECT COUNT(*) FROM P64_ParamRevision WHERE Accepted = 1 "
                       "AND AcceptedDate <> '2026-08-04'").fetchone()[0] == 0


def test_todo_idcp_existe_em_p30_e_e_unico(ref):
    assert ref.execute("SELECT COUNT(*) FROM P64_ParamRevision r LEFT JOIN P30_ControlParam p "
                       "USING (IDCP) WHERE p.IDCP IS NULL").fetchone()[0] == 0
    assert ref.execute("SELECT COUNT(DISTINCT IDCP) FROM P64_ParamRevision").fetchone()[0] == 120
    assert ref.execute("PRAGMA foreign_key_check").fetchall() == []


def test_todo_ajuste_tem_campo_e_valor_sugerido(ref):
    ruins = ref.execute("SELECT COUNT(*) FROM P64_ParamRevision WHERE Action = 'adjust' "
                        "AND (Field IS NULL OR SuggestedValue IS NULL)").fetchone()[0]
    assert ruins == 0


def test_excecoes_de_ligacao(ref):
    ids = {r[0] for r in ref.execute("SELECT IDCP FROM P64_ParamRevision")}
    assert {"X32", "X33", "X94", "X100", "X120"} <= ids
    assert "F156" not in ids


# --------------------------------------------------------------------------
# Nucleo
# --------------------------------------------------------------------------
def test_linhas_do_painel_reproduzem_o_p30(ref):
    rows = pr.panel_rows(ref, 0, "Expert")
    assert len(rows) == 120
    for r in rows:
        dv, lo, mf, hi = ref.execute(
            "SELECT DefaultValue, MinValue, MostFrequent, MaxValue FROM P30_ControlParam "
            "WHERE IDCP = ?", (r.idcp,)).fetchone()
        assert r.value == dv and (r.lo, r.mf, r.hi) == (lo, mf, hi)
        assert r.source == "Default"


def test_resumo(ref):
    s = pr.summary(pr.panel_rows(ref, 0, "Expert"))
    assert s["total"] == 120 and s["spotlight"] == 17 and s["accepted"] == 11
    assert s["by_action"] == {"keep": 106, "adjust": 9, "verify": 5}
    assert s["review_date"] == "2026-08-03"


def test_aviso_de_modulo_ainda_nao_implementado(ref):
    rows = {r.idcp: r for r in pr.panel_rows(ref, 0, "Expert")}
    m4 = [r for r in rows.values() if r.module == "M4"]
    assert m4 and all(r.note == "Recorded — not used until M4" for r in m4)
    assert all(r.note is None for r in rows.values() if r.module in ("M1M2", "UI"))


def test_alertas_recalculados(ref):
    assert pr.consistency_flags(0.3, 0.2, 0.1, 0.2) == (pr.ALERT_INVERTED,)
    assert pr.consistency_flags(0.0, 0.3, 0.2, 0.1) == (pr.ALERT_TYPICAL,)
    assert pr.consistency_flags(0.1, 0.2, 0.3, 0.2) == ()
    assert pr.consistency_flags(0.1, 0.2, 0.3, 0.9) == (pr.ALERT_ADOPTED,)
    assert pr.consistency_flags(None, 0.2, 0.3, 0.9) == ()
    # os alertas do painel vem do P30: CV Auxiliary Systems estava invertido e foi corrigido
    rows = {r.idcp: r for r in pr.panel_rows(ref, 0, "Expert")}
    for r in rows.values():
        assert r.flags == pr.consistency_flags(r.lo, r.mf, r.hi, r.value)


def test_valor_efetivo_segue_o_usuario(mem):
    # D08 do projeto altera o valor mostrado, sem tocar em P30
    mem.execute("PRAGMA foreign_keys = OFF")
    idcp = "X23"
    antes = mem.execute("SELECT DefaultValue FROM P30_ControlParam WHERE IDCP = ?",
                        (idcp,)).fetchone()[0]
    mem.execute("INSERT INTO D08_ControlParamValue (IDA, IDCP, Profile, Value, ValueSource, "
                "UpdatedAt) VALUES (1, ?, 'Expert', 450, 'teste', '2026-11-21')", (idcp,))
    rows = {r.idcp: r for r in pr.panel_rows(mem, 1, "Expert")}
    assert rows[idcp].value == 450 and rows[idcp].source == "User"
    assert mem.execute("SELECT DefaultValue FROM P30_ControlParam WHERE IDCP = ?",
                       (idcp,)).fetchone()[0] == antes


def test_revisao_nova_vira_vigente_e_a_antiga_vira_historico(mem):
    cur = mem.execute("SELECT MAX(IDRV) FROM P64_ParamRevision").fetchone()[0]
    mem.execute(
        "INSERT INTO P64_ParamRevision (IDRV, IDCP, ReviewDate, PanelNo, Action, Rationale) "
        "VALUES (?, 'X23', '2026-12-07', 23, 'verify', 'nova revisao')", (cur + 1,))
    mem.execute("INSERT INTO P65_ParamRevisionSource VALUES (?, 1, 'Fonte nova', '2026')",
                (cur + 1,))
    vigente = pr.latest_by_param(mem)["X23"]
    assert vigente.review_date == "2026-12-07" and vigente.action == "verify"
    assert vigente.sources == (("Fonte nova", "2026"),)
    hist = pr.history(mem, "X23")
    assert [h.review_date for h in hist] == ["2026-12-07", "2026-08-03"]


def test_nucleo_so_le(ref):
    """Nenhuma funcao do painel escreve: a base aberta como somente leitura serve."""
    pr.panel_rows(ref, 0, "Basic")
    pr.latest_by_param(ref)
    pr.history(ref, "X37")


def test_nucleo_sem_streamlit():
    with open(os.path.join(REPO, "core", "param_review.py"), encoding="utf-8") as fh:
        assert "streamlit" not in fh.read().replace("nao importa streamlit", "")


def test_revisao_nao_muda_o_hash_da_base_de_calculo(mem):
    """P64 e P65 so informam: uma revisao nova nao invalida rodadas congeladas."""
    from core import schema
    antes = schema.param_base_hash(mem)
    cur = mem.execute("SELECT MAX(IDRV) FROM P64_ParamRevision").fetchone()[0]
    mem.execute("INSERT INTO P64_ParamRevision (IDRV, IDCP, ReviewDate, PanelNo, Action, "
                "Rationale) "
                "VALUES (?, 'X37', '2026-12-07', 37, 'keep', 'x')", (cur + 1,))
    assert schema.param_base_hash(mem) == antes


# --------------------------------------------------------------------------
# Paridade com o artefato: alertas, notas, formatacao e busca
# --------------------------------------------------------------------------
def _base():
    import sqlite3

    from ui import state
    return sqlite3.connect(f"file:{state.REFERENCE_DB}?mode=ro", uri=True)


def test_alertas_de_novos_desenvolvimentos_vem_da_base():
    c = _base()
    a = pr.alerts(c)
    assert len(a) == 8
    assert [x.severity for x in a][:4] == ["high"] * 4
    assert (23, 25) in [x.panel_nos for x in a]
    assert len(pr.review_texts(c, "note")) == 5
    assert len(pr.review_texts(c, "history")) == 1


def test_formatacao_por_familia_e_percentual():
    rows = pr.panel_rows(_base())
    dec = pr.family_decimals(rows)
    pct = next(r for r in rows if r.unit and "%" in r.unit)
    assert pr.fmt(0.264, pct.unit, dec) == "26.4%"
    assert pr.fmt(None, "kg", dec) == "—"
    assert pr.fmt(1234.5, "(no unit)", {"(no unit)": 1}) == "1,234.5"


def test_busca_por_numero_exato_e_por_bloco():
    rows = pr.panel_rows(_base())
    assert [r.revision.panel_no for r in rows if pr.matches(r, "#23")] == [23]
    assert sum(pr.matches(r, "Fuel Emission") for r in rows) == sum(
        r.section == "FEF" for r in rows)


def test_kpis_do_cabecalho():
    s = pr.summary(pr.panel_rows(_base()))
    assert (s["battery"], s["ice"], s["sources"], s["adjustments"]) == (28, 18, 68, 14)


def test_valor_da_data_base_para_riscado():
    rows = pr.panel_rows(_base())
    assert all(r.revision.panel_no > 0 for r in rows)
    assert any(r.revision.baseline_value is not None for r in rows)
