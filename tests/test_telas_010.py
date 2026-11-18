"""The 0.10 screens (T01 to T11, T41), run headless on a project with one frozen run."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from streamlit.testing.v1 import AppTest  # noqa: E402

from core import analysis, project, run  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOVAS = ["T01_Home", "T02_Vehicle_picker", "T03_Project_configuration",
         "T04_Selected_parameters", "T05_Dashboard", "T06_Multiple_projects",
         "T07_Equations_and_glossary", "T08_Export", "T09_Market_vehicles",
         "T10_Vehicle_parameters", "T11_Default_parameters", "T41_Validate_and_freeze"]


@pytest.fixture(scope="module")
def projeto(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("telas") / "p.sqlite")
    shutil.copyfile(os.path.join(REPO, "data", "base_referencia.sqlite"), path)
    conn = sqlite3.connect(path)
    project.create(conn, "Telas")
    apv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion LIMIT 1").fetchone()[0]
    cfg = dict(fuel="E27", norm="NBR", curve="Default", idefv="BR23", idmpv=1, idapv=apv)
    ida = analysis.create_ec(conn, "EC", "A0", cfg)
    rid = run.freeze(conn, ida, calculator_version="test", reference_workbook="x")
    run.execute(conn, path, rid)
    conn.close()
    return path, rid


def _abrir(tela, projeto=None, **estado):
    at = AppTest.from_file(os.path.join(REPO, "pages", tela + ".py"), default_timeout=120)
    if projeto:
        at.session_state["project_path"] = projeto[0]
        at.session_state["project_name"] = "Telas"
        at.session_state["run_id"] = projeto[1]
        at.session_state["open_projects"] = [{"path": projeto[0], "name": "Telas"}]
        at.session_state["selected_paths"] = [projeto[0]]
    for k, v in estado.items():
        at.session_state[k] = v
    return at.run()


@pytest.mark.parametrize("tela", NOVAS)
def test_abre_com_projeto(tela, projeto):
    at = _abrir(tela, projeto)
    assert not at.exception, at.exception


@pytest.mark.parametrize("tela", [t for t in NOVAS if t not in
                                  ("T01_Home", "T07_Equations_and_glossary",
                                   "T06_Multiple_projects")])
def test_sem_projeto_pede_para_abrir(tela):
    at = _abrir(tela)
    assert not at.exception, at.exception
    assert any("Home" in i.value or "Open or create" in i.value for i in at.info)


def test_dashboard_mostra_selo_em_todo_numero(projeto):
    at = _abrir("T05_Dashboard", projeto)
    tabela = at.dataframe[0].value
    assert len(tabela) > 0
    assert (tabela["Seal"].astype(str).str.len() > 0).all()


def test_t08_exporta_com_hash(projeto):
    at = _abrir("T08_Export", projeto)
    assert not at.exception
    assert any("ExportHash" in c.value for c in at.caption)


def test_t41_congela_e_roda(projeto, tmp_path):
    copia = str(tmp_path / "c.sqlite")
    shutil.copyfile(projeto[0], copia)
    at = _abrir("T41_Validate_and_freeze", (copia, projeto[1]))
    at.button[0].click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(copia)
    assert conn.execute("SELECT COUNT(*) FROM D09_Run").fetchone()[0] == 2


def test_t03_override_de_fator(projeto, tmp_path):
    copia = str(tmp_path / "d.sqlite")
    shutil.copyfile(projeto[0], copia)
    at = _abrir("T03_Project_configuration", (copia, projeto[1]))
    assert not at.exception, at.exception
    assert any("SPHEV" in i.value or "Hatch" in i.value for i in at.info)


def test_t01_tipos_de_analise_sao_os_do_prototipo(projeto):
    at = _abrir("T01_Home", projeto)
    assert not at.exception, at.exception
    box = next(s for s in at.selectbox if s.key == "analysis_type")
    assert list(box.options) == ["GHG LCA and LCC", "Sensitivity Analysis", "Monte Carlo",
                                 "Lightweighting"]
    box.select("Monte Carlo").run()
    assert any("planned" in c.value for c in at.caption)


def test_t01_lista_de_projetos_com_selecao(projeto):
    at = _abrir("T01_Home", projeto)
    assert any(c.label.startswith("PRJ-") for c in at.checkbox)


def test_t01_renomeia_o_projeto(projeto, tmp_path):
    copia = str(tmp_path / "r.sqlite")
    shutil.copyfile(projeto[0], copia)
    at = _abrir("T01_Home", (copia, projeto[1]))
    campo = next(t for t in at.text_input if t.label == "Rename selected project")
    campo.input("Projeto renomeado").run()
    next(b for b in at.button if b.label == "Save name").click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(copia)
    assert conn.execute("SELECT ProjectName FROM M03_Project").fetchone()[0] == \
        "Projeto renomeado"


def test_projeto_de_exemplo_existe_e_e_somente_leitura():
    caminho = os.path.join(REPO, "data", "exemplo.sqlite")
    assert os.path.exists(caminho)
    conn = sqlite3.connect(caminho)
    assert project.identity(conn)["IsExample"] == 1
    assert project.mode(conn) == project.READ
    assert conn.execute("SELECT COUNT(*) FROM D09_Run").fetchone()[0] == 1


def test_t03_salvar_fator_persiste(projeto, tmp_path):
    copia = str(tmp_path / "f.sqlite")
    shutil.copyfile(projeto[0], copia)
    at = _abrir("T03_Project_configuration", (copia, projeto[1]))
    next(n for n in at.number_input if n.key.startswith("kice")).set_value(0.5)
    at.run()
    next(b for b in at.button if b.label == "Save").click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(copia)
    assert conn.execute("SELECT COUNT(*) FROM D12_CombinedPowerOverride").fetchone()[0] == 1


def test_t04_salvar_parametro_persiste(projeto, tmp_path):
    copia = str(tmp_path / "g.sqlite")
    shutil.copyfile(projeto[0], copia)
    at = _abrir("T04_Selected_parameters", (copia, projeto[1]))
    campo = next(n for n in at.number_input if n.key.startswith("v"))
    campo.set_value(float(campo.value) + 0.001)
    at.run()
    next(b for b in at.button if b.label == "Save").click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(copia)
    assert conn.execute("SELECT COUNT(*) FROM D08_ControlParamValue").fetchone()[0] == 1
