"""Entrada por e-mail e senha na T01 e o papel Master nas telas de mercado."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from tests.test_telas_010 import _abrir  # noqa: E402


def _botao(at, rotulo):
    return next(b for b in at.button if b.label == rotulo)


def _campo(at, key):
    return at.text_input(key=key)


def test_t01_primeiro_master_cria_a_conta_e_ve_a_gestao(monkeypatch):
    monkeypatch.setenv("I3ET_MASTER_PASSWORD", "inst-secreta")
    at = _abrir("T01_Home")
    assert not at.exception, at.exception
    _campo(at, "fm_email").set_value("m@x.org")
    _campo(at, "fm_pwd").set_value("senha-longa-1")
    _campo(at, "fm_inst").set_value("errada")
    _botao(at, "Create master account").click().run()
    assert any("Wrong installation" in e.value for e in at.error)
    _campo(at, "fm_inst").set_value("inst-secreta")
    _botao(at, "Create master account").click().run()
    assert not at.exception, at.exception
    assert at.session_state["master_ok"] is True
    assert any("Manage users" in e.label for e in at.expander)


def test_t01_usuario_comum_entra_mas_nao_vira_master(monkeypatch):
    monkeypatch.delenv("I3ET_MASTER_PASSWORD", raising=False)
    at = _abrir("T01_Home")
    _campo(at, "ca_email").set_value("u@x.org")
    _campo(at, "ca_pwd").set_value("senha-longa-1")
    _botao(at, "Create account").click().run()
    assert not at.exception, at.exception
    assert at.session_state["user_email"] == "u@x.org"
    assert not at.session_state["master_ok"]
    assert not any("Manage users" in e.label for e in at.expander)


def test_t01_sair_limpa_a_sessao(monkeypatch):
    monkeypatch.delenv("I3ET_MASTER_PASSWORD", raising=False)
    at = _abrir("T01_Home", user_email="u@x.org", user_role="User", master_ok=False)
    _botao(at, "Sign out").click().run()
    assert not at.exception, at.exception
    assert "user_email" not in at.session_state


def test_t01_sem_master_e_sem_senha_de_instalacao_explica(monkeypatch):
    monkeypatch.delenv("I3ET_MASTER_PASSWORD", raising=False)
    at = _abrir("T01_Home")
    assert any("No master exists yet" in i.value for i in at.info)


def test_t01_senha_errada_nao_entra(monkeypatch):
    monkeypatch.delenv("I3ET_MASTER_PASSWORD", raising=False)
    from core import accounts
    from ui import auth
    with auth.connect() as c:
        accounts.create_account(c, "a@x.org", "senha-longa-1")
    at = _abrir("T01_Home")
    _campo(at, "si_email").set_value("a@x.org")
    _campo(at, "si_pwd").set_value("errada-errada")
    _botao(at, "Sign in").click().run()
    assert any("Wrong e-mail or password" in e.value for e in at.error)
    assert "user_email" not in at.session_state


def test_senha_de_instalacao_lida_do_secrets_com_bom(tmp_path, monkeypatch):
    """O PowerShell 5 grava `Set-Content -Encoding UTF8` com BOM; o app tem de aceitar."""
    from ui import state
    monkeypatch.delenv("I3ET_MASTER_PASSWORD", raising=False)
    arq = tmp_path / "secrets.toml"
    arq.write_bytes(b'\xef\xbb\xbfmaster_password = "abc123"\r\n')
    assert state._segredo_do_arquivo(str(arq), "master_password") == "abc123"
    arq.write_text("isto nao e toml [[", encoding="utf-8")
    assert state._segredo_do_arquivo(str(arq), "master_password") is None
    assert state._segredo_do_arquivo(str(tmp_path / "nao-existe.toml"), "master_password") is None
