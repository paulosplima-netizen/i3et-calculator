"""Onde os projetos ficam gravados.

Hoje (uso local): uma pasta fixa do usuario. Os arquivos `.sqlite` ficam nela, sobrevivem a
reiniciar o Streamlit ou fechar o navegador, e a Home os lista. Sem pasta configurada (por
exemplo, numa publicacao na nuvem), o comportamento antigo continua: pasta temporaria por
sessao e download pelo usuario.

Como a pasta e escolhida (a primeira que existir):
  1. variavel de ambiente `I3ET_PROJECTS_DIR` (vazia = modo temporario);
  2. chave `projects_dir` de `local_settings.json` na raiz do repositorio (fora do git);
  3. nenhuma: modo temporario.

Nuvem, no futuro (Fase C, contas com login e senha): esta e a unica porta de entrada para
gravar e listar projetos. A troca sera uma segunda implementacao com o mesmo contrato
(`root`, `list_projects`, `new_path`), que grava no servidor por usuario autenticado, sem
mexer nas telas. Ver `docs/06` e o item "Contas · Projetos guardados no servidor" do Monday.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_VAR = "I3ET_PROJECTS_DIR"
SETTINGS = os.path.join(REPO, "local_settings.json")


def root() -> str | None:
    """A pasta dos projetos, criada se faltar; None no modo temporario."""
    path = os.environ.get(ENV_VAR)       # definida, mesmo vazia, vence o arquivo
    if ENV_VAR not in os.environ and os.path.exists(SETTINGS):
        try:
            with open(SETTINGS, encoding="utf-8") as fh:
                path = json.load(fh).get("projects_dir")
        except (OSError, ValueError):
            path = None
    if not path:
        return None
    path = os.path.expanduser(path)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return None
    return path


def _slug(nome: str) -> str:
    limpo = "".join(c if c.isalnum() or c in "-_" else "_" for c in nome.strip())
    return limpo or f"projeto_{dt.date.today():%Y%m%d}"


def new_path(name: str, *, persist: bool = True, filename: str | None = None) -> str:
    """Caminho livre para um projeto novo: na pasta fixa, ou numa pasta temporaria."""
    pasta = root() if persist else None
    base = filename or (_slug(name) + ".sqlite")
    if pasta is None:
        return os.path.join(tempfile.mkdtemp(prefix="i3et_"), base)
    stem, ext = os.path.splitext(base)
    candidato, n = os.path.join(pasta, base), 2
    while os.path.exists(candidato):
        candidato = os.path.join(pasta, f"{stem}_{n}{ext}")
        n += 1
    return candidato


def list_projects() -> list[dict]:
    """Projetos da pasta, do mais recente ao mais antigo: path, name, id, modified, size."""
    pasta = root()
    if pasta is None:
        return []
    out = []
    for nome in os.listdir(pasta):
        if not nome.lower().endswith(".sqlite"):
            continue
        caminho = os.path.join(pasta, nome)
        try:
            conn = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
            try:
                row = conn.execute("SELECT ProjectID, ProjectName FROM M03_Project").fetchone()
            finally:
                conn.close()
        except sqlite3.Error:
            continue                                   # nao e um projeto
        if row is None:
            continue
        st = os.stat(caminho)
        out.append({"path": caminho, "id": row[0], "name": row[1],
                    "modified": dt.datetime.fromtimestamp(st.st_mtime),
                    "size": st.st_size})
    return sorted(out, key=lambda e: e["modified"], reverse=True)


def label(entry: dict) -> str:
    return f"{entry['name']} · {entry['id']} · {entry['modified']:%d/%m/%Y %H:%M}"

