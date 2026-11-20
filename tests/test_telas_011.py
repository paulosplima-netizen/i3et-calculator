"""Telas do 0.11 (B1), abertas sem navegador sobre um projeto com uma rodada."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from tests.test_telas_010 import _abrir, projeto  # noqa: E402,F401


def test_t18_vida_do_veiculo_abre_e_soma_os_estagios(projeto):  # noqa: F811
    at = _abrir("T18_Vehicle_life", projeto)
    assert not at.exception, at.exception
    tabela = at.dataframe[0].value
    estagios = tabela[tabela["Stage"] != "Vehicle life, without use of energy"]
    total = tabela[tabela["Stage"] == "Vehicle life, without use of energy"]
    col = [c for c in tabela.columns if c.startswith("GHG")][0]
    assert abs(estagios[col].sum() - total[col].iloc[0]) < 0.2


def test_t18_fundida_mostra_o_berco_ao_portao_e_o_detalhe(projeto):  # noqa: F811
    """A T18 reune a antiga Results (0.9) e a Vehicle life: totais, grupo, material, bateria."""
    at = _abrir("T18_Vehicle_life", projeto)
    assert not at.exception, at.exception
    valores = {m.label: m.value for m in at.metric}
    assert "Cradle to gate (kg CO₂e)" in valores, list(valores)
    abas = [t.label for t in at.tabs]
    for esperado in ("Life stages", "By GREET group", "By material", "Battery", "Assembly"):
        assert esperado in abas, abas
    # o total do berco ao portao da metrica e a producao inicial da aba de etapas
    tabela = at.dataframe[0].value
    col = [c for c in tabela.columns if c.startswith("GHG")][0]
    inicial = tabela[tabela["Stage"].str.startswith("Initial production")][col].iloc[0]
    berco = float(valores["Cradle to gate (kg CO₂e)"].replace(",", ""))
    assert abs(inicial - berco) < 0.2, (inicial, berco)


def test_t18_sem_projeto_pede_para_abrir():
    at = _abrir("T18_Vehicle_life")
    assert not at.exception
    assert any("Home" in i.value or "Open or create" in i.value for i in at.info)


@pytest.mark.parametrize("tela", ["T16_Maintenance", "T17_End_of_life"])
def test_t16_t17_abrem_com_projeto(tela, projeto):  # noqa: F811
    at = _abrir(tela, projeto)
    assert not at.exception, at.exception


def test_t17_grava_o_metodo(projeto):  # noqa: F811
    import sqlite3
    at = _abrir("T17_End_of_life", projeto)
    at.radio[0].set_value("EXCLUDED").run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    assert conn.execute("SELECT EoLMethod FROM D06_Analysis").fetchone()[0] == "EXCLUDED"
    conn.execute("UPDATE D06_Analysis SET EoLMethod = 'GLIDER_BATTERY'")
    conn.commit()
    conn.close()


def test_t16_grava_o_cenario(projeto):  # noqa: F811
    import sqlite3
    at = _abrir("T16_Maintenance", projeto)
    at.radio[0].set_value("Sim Bat").run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    assert conn.execute("SELECT MaintenanceMode FROM D10_MaintenanceScenario").fetchone()[0] \
        == "Sim Bat"
    conn.execute("DELETE FROM D10_Item")
    conn.execute("DELETE FROM D10_MaintenanceScenario")
    conn.commit()
    conn.close()


def test_t38_abre_e_grava_a_massa_declarada(projeto):  # noqa: F811
    import sqlite3
    at = _abrir("T38_Mass_validation", projeto)
    assert not at.exception, at.exception
    declarada = [n for n in at.number_input if n.label == "Declared mass (kg)"][0]
    declarada.set_value(1500.0).run()
    [b for b in at.button if b.label == "Save"][0].click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    assert conn.execute("SELECT DeclaredMassKg FROM D07_AnalysisVehicle "
                        "WHERE IDCase = 1").fetchone()[0] == 1500.0
    conn.execute("UPDATE D07_AnalysisVehicle SET DeclaredMassKg = NULL")
    conn.commit()
    conn.close()


def test_t15_abre_cria_versao_e_edita(projeto):  # noqa: F811
    import sqlite3
    at = _abrir("T15_Emission_factors", projeto)
    assert not at.exception, at.exception
    assert len(at.tabs) == 4
    conn = sqlite3.connect(projeto[0])
    from core import ef_edit
    ef_edit.create_version(conn, "MEU-T15", "x", "BR23", "teste")
    conn.commit()
    conn.close()
    at = _abrir("T15_Emission_factors", projeto)
    assert not at.exception, at.exception


def test_t14_abre_com_receita_do_usuario(projeto):  # noqa: F811
    import sqlite3

    from core import user_recipes
    at = _abrir("T14_Materials_recipes", projeto)
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    base_id = conn.execute("SELECT IDVMR FROM P15_VehicleMaterialRecipe LIMIT 1").fetchone()[0]
    user_recipes.copy_recipe(conn, "U-T14", base_id, "teste")
    conn.commit()
    conn.close()
    at = _abrir("T14_Materials_recipes", projeto)
    assert not at.exception, at.exception
    assert len(at.tabs) == 3


def test_t46_abre_e_lista_copias(projeto):  # noqa: F811
    import sqlite3

    from core import user_assets
    at = _abrir("T46_Battery_assembly", projeto)
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    src = conn.execute("SELECT IDBMd FROM P19_BatteryModel WHERE GHGMethod = 'composition' "
                       "LIMIT 1").fetchone()[0]
    user_assets.copy_battery(conn, "UB-T46", src, "teste")
    conn.commit()
    conn.close()
    at = _abrir("T46_Battery_assembly", projeto)
    assert not at.exception, at.exception
    assert len(at.tabs) == 4


def test_t12_t13_abrem_e_t13_lista_copias(projeto):  # noqa: F811
    import sqlite3

    from core import user_mass_params
    for tela in ("T12_Subsystems", "T13_Mass_parameters"):
        at = _abrir(tela, projeto)
        assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    base = conn.execute("SELECT MIN(IDMPV) FROM P05_MassParamVersion").fetchone()[0]
    user_mass_params.copy_version(conn, "UM-T13", base, "teste")
    conn.commit()
    conn.close()
    at = _abrir("T13_Mass_parameters", projeto)
    assert not at.exception, at.exception


def test_t14_lista_de_materiais_acumulada_do_veiculo(projeto):  # noqa: F811
    """'All groups' soma os materiais do veiculo (e da bateria) e fecha com a massa da C11."""
    at = _abrir("T14_Materials_recipes", projeto)
    assert not at.exception, at.exception
    grupo = next(s for s in at.selectbox if s.label == "Group")
    assert grupo.options[0].startswith("All groups")
    grupo.select("__all__").run()
    assert not at.exception, at.exception
    assert any(m.label == "Total mass in the list (kg)" for m in at.metric)
    com = float(next(m for m in at.metric if m.label.startswith("Total mass")).value
                .replace(",", ""))
    assert com > 0
    caixa = next(c for c in at.checkbox if c.label.startswith("Include the traction"))
    caixa.uncheck().run()
    assert not at.exception, at.exception
    sem = float(next(m for m in at.metric if m.label.startswith("Total mass")).value
                .replace(",", ""))
    assert sem <= com


def test_vehicle_bill_fecha_com_c11():
    import pandas as pd

    from core import materials, totals
    c03 = pd.DataFrame({"IDGG": ["G1", "G2", "G2"], "IDM": ["a", "a", "p"],
                        "DsM": ["A", "A", "Proc"], "MassIDMpGG": [10.0, 5.0, 0.0],
                        "GHGIDMpGG": [1.0, 1.0, 1.0], "CountsAsMass": [1, 1, 0]})
    c07 = pd.DataFrame({"IDGG": ["B"], "IDM": ["b"], "DsM": ["B"], "MassIDMpGGB": [20.0],
                        "GHGIDMpGGB": [2.0], "CountsAsMass": [1]})
    full = materials.vehicle_bill(c03, c07)
    assert abs(full["MassKg"].sum() - 35.0) < 1e-9
    assert "p" not in set(full["IDM"])
    assert abs(full["ShareOfMass"].sum() - 1) < 1e-9
    nobat = materials.vehicle_bill(c03, c07, include_battery=False)
    assert abs(nobat["MassKg"].sum() - 15.0) < 1e-9
    c11 = totals.by_material(c03, c07)
    assert abs(c11["MassIDM"].sum() - 35.0) < 1e-9
