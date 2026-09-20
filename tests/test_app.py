"""The screens, run headless.

Streamlit's own test harness executes a page script the way the browser would
and fails if it raises. It does not check that the layout is pretty -- it
checks that every screen opens, with a project and without one, and that the
actions that write to the project file do what they say.

A page that crashes on an empty project, or after a vehicle is added, is the
kind of defect that only shows up in front of whoever is using it.
"""

from __future__ import annotations

import os
import shutil

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from streamlit.testing.v1 import AppTest  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGINAS = [
    "pages/1_Home.py",
    "pages/2_Vehicles.py",
    "pages/3_Vehicle_parameters.py",
    "pages/4_Scenario.py",
    "pages/5_Results.py",
    "pages/6_Emission_factors.py",
    "pages/7_Export.py",
]


@pytest.fixture
def projeto(tmp_path):
    """A project file of its own, so a test never writes on the reference."""
    destino = str(tmp_path / "projeto_teste.sqlite")
    shutil.copyfile(os.path.join(REPO, "data", "base_referencia.sqlite"), destino)
    return destino


def _abrir(pagina: str, projeto: str | None = None, timeout: int = 90) -> AppTest:
    at = AppTest.from_file(os.path.join(REPO, pagina), default_timeout=timeout)
    if projeto:
        at.session_state["project_path"] = projeto
        at.session_state["project_name"] = "projeto_teste"
    return at.run()


@pytest.mark.parametrize("pagina", PAGINAS)
def test_every_screen_opens_with_a_project(pagina, projeto):
    at = _abrir(pagina, projeto)
    assert not at.exception, f"{pagina}: {at.exception}"


@pytest.mark.parametrize("pagina", PAGINAS)
def test_no_screen_crashes_without_a_project(pagina):
    """Sem projeto aberto, a tela orienta em vez de quebrar."""
    at = _abrir(pagina)
    assert not at.exception, f"{pagina}: {at.exception}"


def test_the_home_screen_offers_to_create_a_project():
    at = _abrir("pages/1_Home.py")
    rotulos = [b.label for b in at.button]
    assert any("Create" in r for r in rotulos), rotulos


def test_the_version_bar_states_the_four_versions(projeto):
    """As quatro versoes e a fronteira, inteiras -- nao cortadas numa caixa."""
    at = _abrir("pages/5_Results.py", projeto)
    barra = " ".join(m.value for m in at.markdown)
    for esperado in ("Mass params", "Material recipe", "Emission factors",
                     "Assembly", "Boundary", "MAT_ASM"):
        assert esperado in barra, barra[:400]
    # seis receitas nao cabem na linha: as duas primeiras, e o resto contado
    assert "+4" in barra, barra[:400]


def test_the_results_screen_shows_the_cradle_to_gate_total(projeto):
    at = _abrir("pages/5_Results.py", projeto)
    valores = {m.label: m.value for m in at.metric}
    assert "Cradle to gate (kg CO₂e)" in valores, list(valores)
    # o numero cabe inteiro na caixa: sem reticencias, com separador brasileiro
    assert "…" not in valores["Cradle to gate (kg CO₂e)"]
    assert "." in valores["Cradle to gate (kg CO₂e)"]


def test_the_scenario_screen_offers_both_recipe_families(projeto):
    at = _abrir("pages/4_Scenario.py", projeto)
    opcoes = [o for r in at.radio for o in r.options]
    assert any(str(o).startswith("PBP_") for o in opcoes), opcoes
    assert any(str(o).startswith("BISD") for o in opcoes), opcoes


def test_a_new_vehicle_lands_in_the_project(projeto):
    from core import loader

    at = _abrir("pages/2_Vehicles.py", projeto)
    antes = len(loader.load_sqlite(projeto)["D01"])
    at.text_input[0].set_value("TESTE01")
    at.button[0].click().run()
    assert not at.exception, at.exception
    depois = loader.load_sqlite(projeto)
    assert len(depois["D01"]) == antes + 1
    assert "TESTE01" in set(depois["D01"]["DsV"])
    # e o veiculo novo ja tem cenario e parametros, senao as telas seguintes
    # o mostrariam pela metade
    novo = int(depois["D01"][depois["D01"]["DsV"] == "TESTE01"].iloc[0]["IDV"])
    assert (depois["D02"]["IDV"] == novo).any()
    assert (depois["D03"]["IDV"] == novo).sum() > 30


def test_the_reference_vehicles_cannot_be_edited(projeto):
    at = _abrir("pages/3_Vehicle_parameters.py", projeto)
    assert not at.exception
    avisos = " ".join(i.body for i in at.info)
    assert "read-only" in avisos, avisos


def test_a_user_factor_version_requires_provenance(projeto):
    from core import loader

    at = _abrir("pages/6_Emission_factors.py", projeto)
    at.text_input[0].set_value("MEUS")
    at.text_input[1].set_value("Fatores de teste")
    at.button[0].click().run()          # sem procedencia
    assert not at.exception
    assert len(loader.load_sqlite(projeto)["D04"]) == 0
    assert any("Provenance is required" in e.value for e in at.error)


def test_the_export_screen_lists_what_will_come_out(projeto):
    at = _abrir("pages/7_Export.py", projeto)
    assert not at.exception
    assert at.dataframe, "a previa das tabelas sumiu"
