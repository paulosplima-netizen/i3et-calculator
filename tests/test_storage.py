"""Pasta fixa dos projetos (ui/storage.py): sobrevive a reiniciar e e listada na Home."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from core import project  # noqa: E402
from tests.test_telas_010 import _abrir  # noqa: E402
from ui import state, storage  # noqa: E402


def test_sem_pasta_configurada_usa_o_modo_temporario():
    assert storage.root() is None
    assert storage.list_projects() == []
    assert "i3et_" in storage.new_path("x")


def test_pasta_fixa_guarda_lista_e_nao_sobrescreve(tmp_path, monkeypatch):
    monkeypatch.setenv("I3ET_PROJECTS_DIR", str(tmp_path / "Projetos"))
    a = storage.new_path("meu projeto")
    assert os.path.dirname(a) == str(tmp_path / "Projetos")
    shutil.copyfile(state.REFERENCE_DB, a)
    conn = sqlite3.connect(a)
    project.create(conn, "meu projeto")
    conn.commit()
    conn.close()
    assert storage.new_path("meu projeto") != a            # nome livre: _2
    lista = storage.list_projects()
    assert [e["name"] for e in lista] == ["meu projeto"]
    assert storage.label(lista[0]).startswith("meu projeto")


def test_arquivo_que_nao_e_projeto_e_ignorado(tmp_path, monkeypatch):
    monkeypatch.setenv("I3ET_PROJECTS_DIR", str(tmp_path))
    (tmp_path / "lixo.sqlite").write_bytes(b"nao e sqlite")
    sqlite3.connect(tmp_path / "vazio.sqlite").close()
    assert storage.list_projects() == []


def test_home_lista_os_projetos_salvos(tmp_path, monkeypatch):
    monkeypatch.setenv("I3ET_PROJECTS_DIR", str(tmp_path))
    dest = storage.new_path("guardado")
    shutil.copyfile(state.REFERENCE_DB, dest)
    conn = sqlite3.connect(dest)
    project.create(conn, "guardado")
    conn.commit()
    conn.close()
    at = _abrir("T01_Home")
    assert not at.exception, at.exception
    pick = next(s for s in at.selectbox if s.label == "Open a saved project")
    assert pick.options                                  # o projeto aparece sem sessao previa
    next(b for b in at.button if b.label == "Open saved project").click().run()
    assert not at.exception, at.exception
    assert at.session_state["project_path"] == dest


def test_o_mesmo_arquivo_carregado_tem_a_mesma_marca():
    """Regressao de 21/11/2026: o seletor mantem o arquivo apos o rerun; a Home so abre
    um arquivo se a marca for nova (senao grava uma copia por recarga)."""
    pytest.importorskip("streamlit")
    from ui import state

    class Arq:
        def __init__(self, nome, tamanho, fid=None):
            self.name, self.size, self.file_id = nome, tamanho, fid

    a = Arq("p.sqlite", 10, "x1")
    assert state.upload_token(a) == state.upload_token(Arq("p.sqlite", 10, "x1"))
    assert state.upload_token(a) != state.upload_token(Arq("p.sqlite", 10, "x2"))
    assert state.upload_token(a) != state.upload_token(Arq("q.sqlite", 10, "x1"))
