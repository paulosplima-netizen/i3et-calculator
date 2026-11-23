"""Telas do 0.11 (B1), abertas sem navegador sobre um projeto com uma rodada."""

from __future__ import annotations

import os
import sqlite3

import pytest

pytest.importorskip("streamlit", reason="interface nao instalada neste ambiente")
from tests.test_telas_010 import REPO, _abrir, projeto  # noqa: E402,F401


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


def test_t15_aplica_as_casas_decimais_do_formato(projeto):  # noqa: F811
    """O fator de emissao da T15 segue as casas decimais da T47 (classe 'factor')."""
    import sqlite3

    from core import formatting as fm
    at = _abrir("T15_Emission_factors", projeto)
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    conn.close()
    tab = next(d.value for d in at.dataframe if "EF" in d.value.columns)
    casas = fm.DEFAULT.decimals["factor"]
    vals = tab["EF"].dropna()
    assert len(vals) and all(abs(v - round(v, casas)) < 1e-12 for v in vals)


def test_t08_prepara_excel_csv_e_relatorio_no_formato_da_t47(projeto):  # noqa: F811
    at = _abrir("T08_Export", projeto)
    assert not at.exception, at.exception
    botao = next(b for b in at.button if b.label == "Prepare Excel, CSV and report")
    botao.click().run()
    assert not at.exception, at.exception
    pronto = at.session_state["t08_files"]
    assert pronto[0] == projeto[1]
    assert set(pronto[1]) == {"xlsx", "zip", "html"} and all(pronto[1].values())
    import io

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(pronto[1]["xlsx"]))
    assert "R10" in wb.sheetnames and "R14" in wb.sheetnames


def test_t05_e_t06_seguem_o_formato(projeto):  # noqa: F811
    import sqlite3

    from core import formatting as fm
    conn = sqlite3.connect(projeto[0])
    cru = conn.execute("SELECT Value FROM R45_PowertrainSummary WHERE IDInd = 'O20' AND "
                       "Value IS NOT NULL LIMIT 1").fetchone()[0]
    conn.close()
    texto, unidade = fm.indicator(cru, "kg", fm.DEFAULT)
    assert texto == fm.fmt(cru, "mass", fm.DEFAULT) and unidade == "kg"
    for tela in ("T05_Dashboard", "T06_Multiple_projects"):
        at = _abrir(tela, projeto)
        assert not at.exception, (tela, at.exception)


def test_formatting_indicator_converte_para_toneladas():
    from core import formatting as fm
    f = fm.Format(ghg_unit="t", mass_unit="t")
    assert fm.indicator(4500.0, "kg CO2e/v", f)[1] == "t CO₂e/v"
    assert fm.indicator(1500.0, "kg", f)[1] == "t"
    assert fm.indicator(None, "kW", f) == ("", "kW")


# --------------------------------------------------------------------------
# Painel de parametros (T48)
# --------------------------------------------------------------------------
def _html(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_t48_abre_e_mostra_os_120_parametros(projeto):  # noqa: F811
    at = _abrir("T48_Parameter_review", projeto)
    assert not at.exception, at.exception
    valores = {m.label: m.value for m in at.metric}
    assert valores["Parameters"] == "120"
    assert (valores["Battery"], valores["Combustion engines"]) == ("28", "18")
    assert (valores["Distinct sources"], valores["Alerts"], valores["Adjustments"]) == (
        "68", "8", "14")
    assert _html(at).count("<tr><td") == 120


def test_t48_filtro_por_recomendacao(projeto):  # noqa: F811
    at = _abrir("T48_Parameter_review", projeto)
    at.radio(key="review_filter").set_value("With recommendation").run()
    assert not at.exception, at.exception
    assert _html(at).count("<tr><td") == 14


def test_t48_busca_por_numero_e_por_fonte(projeto):  # noqa: F811
    at = _abrir("T48_Parameter_review", projeto)
    at.text_input[0].set_value("#23").run()
    assert not at.exception, at.exception
    assert _html(at).count("<tr><td") == 1


def test_t48_nao_altera_o_projeto(projeto):  # noqa: F811
    import sqlite3
    conn = sqlite3.connect(projeto[0])
    antes = conn.execute("SELECT COUNT(*) FROM D08_ControlParamValue").fetchone()[0]
    conn.close()
    at = _abrir("T48_Parameter_review", projeto)
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    assert conn.execute("SELECT COUNT(*) FROM D08_ControlParamValue").fetchone()[0] == antes
    conn.close()


def test_t04_aceita_o_parametro_vindo_da_t48(projeto):  # noqa: F811
    at = _abrir("T04_Selected_parameters", projeto)
    at.session_state["t04_prefill"] = "X37"
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["t04_term"] == "X37"


def test_t48_abre_sem_projeto_e_sem_analise():
    """Consulta independente de projeto (como o artefato original): vem da base."""
    at = _abrir("T48_Parameter_review")
    assert not at.exception, at.exception
    valores = {m.label: m.value for m in at.metric}
    assert valores["Parameters"] == "120" and valores["Alerts"] == "8"
    assert _html(at).count("<tr><td") == 120
    assert any("New developments" in e.label for e in at.expander)


def test_t48_valor_adotado_e_o_do_catalogo():
    at = _abrir("T48_Parameter_review")
    html = _html(at)
    assert "Adopted" in html and "Reading notes" in " ".join(s.value for s in at.subheader)
    assert "400" in html




def test_t48_coluna_adopted_segue_o_projeto_aberto(projeto, tmp_path):  # noqa: F811
    import shutil
    import sqlite3

    from core import control_params as cp
    copia = str(tmp_path / "editado.sqlite")
    shutil.copyfile(projeto[0], copia)
    conn = sqlite3.connect(copia)
    ida = conn.execute("SELECT MAX(IDA) FROM D06_Analysis").fetchone()[0]
    perfil = conn.execute("SELECT ParamProfile FROM D06_Analysis WHERE IDA=?",
                          (ida,)).fetchone()[0]
    cp.set_value(conn, ida, "X23", perfil, value=450.0, source="teste")
    conn.commit()
    conn.close()
    at = _abrir("T48_Parameter_review", (copia, projeto[1]))
    assert not at.exception, at.exception
    html = _html(at)
    assert "Adopted in Telas" in html
    assert "edited in this project" in html and "<b>450</b>" in html
    assert "<s style='color:#9ca3af'>400</s>" in html
    assert any("1 edited" in c.value for c in at.caption)


def test_t48_sem_projeto_o_titulo_e_o_do_modelo_excel():
    at = _abrir("T48_Parameter_review")
    assert "Adopted in Excel Model LCA_LV_i3ET_20261119" in _html(at)
    assert "edited in this project" not in _html(at)


def test_t48_sem_master_nao_ha_controle_de_master():
    at = _abrir("T48_Parameter_review")
    assert not at.exception, at.exception
    assert not any(b.key == "accept_ruler" for b in at.button)


def test_t48_master_aceita_e_desfaz_a_regua_sem_mexer_no_adotado(monkeypatch, tmp_path):
    import shutil
    import sqlite3

    from ui import state
    base = str(tmp_path / "base.sqlite")
    shutil.copyfile(state.REFERENCE_DB, base)
    monkeypatch.setenv("I3ET_REFERENCE_DB", base)
    at = _abrir("T48_Parameter_review")
    assert not at.exception, at.exception
    assert not any(b.key == "accept_X75" for b in at.button)         # ainda sem acesso
    at = _abrir("T48_Parameter_review", user_email="m@x.org", user_role="Master",
                master_ok=True)
    assert not at.exception, at.exception
    assert any("Suggestions to accept (1)" in e.label for e in at.expander)
    antes = sqlite3.connect(base).execute(
        "SELECT DefaultValue, MinValue, MostFrequent, MaxValue FROM P30_ControlParam "
        "WHERE IDCP='X75'").fetchone()
    at.button(key="accept_X75").click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(base)
    assert conn.execute("SELECT Field, Value FROM P69_ParamRangeAccept WHERE IDCP='X75'"
                        ).fetchone() == ("mf", 240.0)
    assert conn.execute("SELECT DefaultValue, MinValue, MostFrequent, MaxValue "
                        "FROM P30_ControlParam WHERE IDCP='X75'").fetchone() == antes
    assert "accepted by master" in _html(at)
    at.button(key="undo_X75").click().run()
    assert sqlite3.connect(base).execute("SELECT COUNT(*) FROM P69_ParamRangeAccept"
                                         ).fetchone()[0] == 0


def test_t48_colunas_alinhadas_entre_blocos_e_numeros_centralizados():
    import re
    at = _abrir("T48_Parameter_review")
    html = _html(at)
    colgroups = re.findall(r"<colgroup>.*?</colgroup>", html)
    assert len(colgroups) >= 7 and len(set(colgroups)) == 1
    assert html.count("table-layout:fixed") == len(colgroups)
    assert "text-align:center" in html


def _t48_idcp_editavel():
    import sqlite3 as _s

    from core import control_params as cp
    from core import param_review as pr
    with _s.connect(os.path.join(REPO, "data", "base_referencia.sqlite")) as c:
        calc = {i for (i,) in c.execute("SELECT IDCP FROM P30_ControlParam WHERE IsCalculated=1")}
        return next(r.idcp for r in pr.panel_rows(c)
                    if r.idcp not in calc and r.name not in cp.CONFIG_LINKED
                    and r.default is not None)


def test_t48_edicao_desligada_por_padrao_e_sem_projeto(projeto):  # noqa: F811
    at = _abrir("T48_Parameter_review")
    assert at.toggle(key="t48_edit_on").disabled
    at = _abrir("T48_Parameter_review", projeto)
    assert not at.toggle(key="t48_edit_on").value
    assert not at.toggle(key="t48_edit_on").disabled
    assert not [b for b in at.button if b.key == "t48_apply"]


def test_t48_aplica_nos_tres_perfis_e_a_t04_enxerga(projeto):  # noqa: F811
    from core import control_params as cp
    idcp = _t48_idcp_editavel()
    at = _abrir("T48_Parameter_review", projeto)
    at.selectbox(key="review_pick").set_value(idcp).run()
    at.toggle(key="t48_edit_on").set_value(True).run()
    assert not at.exception, at.exception
    novo = at.number_input(key=f"t48_v_{idcp}")
    novo.set_value(novo.value + 1.0).run()
    apply = next(b for b in at.button if b.key == "t48_apply")
    assert apply.disabled                       # fonte obrigatoria
    at.text_input(key=f"t48_s_{idcp}").set_value("teste").run()
    next(b for b in at.button if b.key == "t48_apply").click().run()
    assert not at.exception, at.exception
    conn = sqlite3.connect(projeto[0])
    try:
        ida = conn.execute("SELECT MAX(IDA) FROM D06_Analysis").fetchone()[0]
        n = conn.execute("SELECT COUNT(*) FROM D08_ControlParamValue WHERE IDA=? AND IDCP=?",
                         (ida, idcp)).fetchone()[0]
        assert n == 3
        for perfil in cp.PROFILES:
            assert cp.effective_values(conn, ida, perfil)[idcp].source == "User"
        cp.restore_all(conn, ida)
        conn.commit()
    finally:
        conn.close()


def test_t48_master_somente_leitura_bloqueia_edicao():
    at = _abrir("T48_Parameter_review", (os.path.join(REPO, "data", "exemplo.sqlite"), 1))
    assert at.toggle(key="t48_edit_on").disabled
