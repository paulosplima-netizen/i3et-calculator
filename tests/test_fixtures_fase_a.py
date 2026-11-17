"""Fixtures da Fase A (passo 3): o que a base de referencia passou a conter.

Cada teste confere um numero ou uma relacao que o levantamento da planilha
LCA_LV_i3ET_20261101.xlsx registrou. Se a planilha de referencia mudar, sao
estes os numeros a rever.
"""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import calc, loader, schema

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
PROJETO_090 = os.path.join(REPO, "tests", "fixtures", "base_090.sqlite")


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    yield c
    c.close()


def um(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


# --------------------------------------------------------------------------
# A base inteira
# --------------------------------------------------------------------------
def test_base_integra_e_com_impressao_digital_atual(conn):
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert um(conn, "SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'") \
        == schema.param_base_hash(conn)
    assert um(conn, "SELECT COUNT(*) FROM M03_Project") == 0      # a base nao e projeto


def test_dicionario_em_dados_cobre_as_tabelas_novas(conn):
    for tabela in schema.TABLES_010:
        n = um(conn, "SELECT COUNT(*) FROM P01_DataDictionary WHERE IDTable = ?",
               tabela.split("_")[0])
        assert n == len(conn.execute(f"PRAGMA table_info({tabela})").fetchall()), tabela
    assert um(conn, "SELECT COUNT(*) FROM P01_DataDictionary WHERE IDTable IN "
                    "('P26','P30','D06','M03') AND DsColumnName IS NULL") == 0


# --------------------------------------------------------------------------
# Market Vehicles (P54, P26, P27)
# --------------------------------------------------------------------------
def test_catalogo_de_veiculos_de_mercado(conn):
    assert um(conn, "SELECT COUNT(*) FROM P54_MarketParam") == 58
    assert um(conn, "SELECT COUNT(*) FROM P26_MarketVehicle") == 154
    assert [r[0] for r in conn.execute(
        "SELECT IDMV FROM P26_MarketVehicle WHERE IsSelecao = 1 ORDER BY IDMV")] \
        == [7, 18, 33, 43, 62, 83]
    assert dict(conn.execute(
        "SELECT SalesClass, COUNT(*) FROM P26_MarketVehicle GROUP BY 1")) \
        == {"V": 60, "CL": 50, "ND": 44}


def test_parametros_do_nucleo_tem_o_mesmo_numero_nas_duas_tabelas(conn):
    """P54 aponta para P07 nos parametros 2 a 40, e os nomes conferem."""
    linhas = conn.execute(
        "SELECT m.IDMP, m.DsMP, v.DsVP FROM P54_MarketParam m "
        "JOIN P07_VehicleParam v ON v.IDVP = m.IDVP").fetchall()
    assert len(linhas) == 39
    for idmp, mercado, nucleo in linhas:
        assert mercado[:12].lower() == nucleo[:12].lower() or idmp in (9, 16, 25), idmp


def test_selecao_tem_dez_medias_e_o_resto_vem_do_representativo(conn):
    for idmv in (7, 18, 33, 43, 62, 83):
        assert um(conn, "SELECT COUNT(*) FROM P27_MarketVehicleParam "
                        "WHERE IDMV = ? AND ValueClass = 'Avg'", idmv) == 10
        rep = um(conn, "SELECT IDMVRepresentative FROM P26_MarketVehicle WHERE IDMV = ?", idmv)
        assert rep == idmv + 1


def test_veiculos_fora_do_calculo_estao_marcados(conn):
    assert dict(conn.execute("SELECT IDVPT, IsCalculable FROM P12_Powertrain")) == {
        "ICEV": 1, "HEV": 1, "SHEV": 1, "PHEV": 1, "SPHEV": 1, "BEV": 1,
        "MHEV": 0, "FCEV": 0}
    assert dict(conn.execute(
        "SELECT IDVDT, IsCalculable FROM P13_DesignType WHERE IsCalculable = 0")) \
        == {"Van": 0, "Chassis": 0}
    assert um(conn, "SELECT COUNT(*) FROM P26_MarketVehicle "
                    "WHERE IDVDT IN ('Van','Chassis')") == 25
    assert um(conn, "SELECT COUNT(*) FROM P12_Powertrain WHERE DsVPT = 'blblblbl'") == 0


# --------------------------------------------------------------------------
# PBEV (P36, P28, P55, P50)
# --------------------------------------------------------------------------
def test_edicao_do_pbev_e_seus_vinculos(conn):
    assert um(conn, "SELECT COUNT(*) FROM P28_PBEVRecord WHERE IDPBE = 'PBEV2026'") == 843
    assert um(conn, "SELECT RecordCount FROM P36_PBEVEdition") == 843
    assert um(conn, "SELECT COUNT(DISTINCT IDMV) FROM P50_MarketVehiclePBEV") == 92
    assert um(conn, "SELECT COUNT(*) FROM (SELECT IDMV FROM P50_MarketVehiclePBEV "
                    "GROUP BY IDMV HAVING COUNT(*) > 1)") == 64
    # um, e so um, primeiro registro por veiculo: o que a busca da planilha devolve
    assert um(conn, "SELECT COUNT(*) FROM P50_MarketVehiclePBEV WHERE IsFirstMatch = 1") == 92


# --------------------------------------------------------------------------
# Control Panel (P29, P30, P51, P52)
# --------------------------------------------------------------------------
def test_categorias(conn):
    assert conn.execute(
        "SELECT c.IDVC, c.CaseDigit, s.DsMV, r.DsMV FROM P29_VehicleCategory c "
        "JOIN P26_MarketVehicle s ON s.IDMV = c.IDMVSelecao "
        "JOIN P26_MarketVehicle r ON r.IDMV = c.IDMVRepresentative ORDER BY 1").fetchall() == [
        ("A0", 0, "SELEÇÃO HATCH C", "FIAT ARGO"), ("A1", 1, "SELEÇÃO SUV C", "HYUNDAI CRETA"),
        ("A2", 2, "SELEÇÃO SEDAN CM", "VW VIRTUS"), ("A3", 3, "SELEÇÃO SUV ML", "JEEP COMPASS"),
        ("A4", 4, "SELEÇÃO PUT L", "TOYOTA HILUX"), ("A5", 5, "SELEÇÃO PUT C", "FIAT STRADA")]


def test_catalogo_de_parametros_do_painel(conn):
    assert dict(conn.execute("SELECT Level, COUNT(*) FROM P30_ControlParam GROUP BY 1")) \
        == {"B": 12, "E": 108, "X": 85}
    assert um(conn, "SELECT COUNT(*) FROM P30_ControlParam WHERE IsCalculated = 1") == 66
    assert dict(conn.execute("SELECT Section, COUNT(*) FROM P30_ControlParam GROUP BY 1")) \
        == {"AUC": 67, "PET": 51, "UPP": 26, "MEF": 22, "FEF": 18, "LWP": 15, "LMP": 6}
    assert um(conn, "SELECT COUNT(*) FROM P30_ControlParam WHERE UsedByModule IS NULL") == 0


def test_bloco_basic_tem_valores_proprios(conn):
    basic = dict(conn.execute(
        "SELECT IDCP, BasicValue FROM P30_ControlParam WHERE BasicValue IS NOT NULL"))
    assert len(basic) == 9
    assert basic["X79"] == 28.68 and basic["X66"] == 0.17 and basic["X83"] == 11.5
    # e diferem do Expert em quatro parametros, como registrado em 11/11
    assert um(conn, "SELECT COUNT(*) FROM P30_ControlParam WHERE IDCP IN "
                    "('X35','X66','X79','X83') AND ABS(BasicValue - DefaultValue) > 1e-9") == 4


def test_tabela_de_saidas(conn):
    assert um(conn, "SELECT COUNT(*) FROM P51_OutputIndicator") == 47
    assert um(conn, "SELECT COUNT(*) FROM P51_OutputIndicator WHERE IsHeader = 1") == 3
    assert um(conn, "SELECT CalcStatus FROM P51_OutputIndicator WHERE IDInd = 'O29'") \
        == "Calculated"                                  # GEE de fabricacao
    assert um(conn, "SELECT CalcStatus FROM P51_OutputIndicator WHERE IDInd = 'O22'") \
        == "ExcelReference"                              # intensidade energetica (M3)


def _ref(conn, conjunto, indicador):
    return [round(r[0], 2) for r in conn.execute(
        "SELECT Value FROM P52_ExcelReferenceValue WHERE RefSet = ? AND IDInd = ? "
        "ORDER BY CaseKey", (conjunto, indicador))]


def test_valores_gravados_da_rodada_de_referencia(conn):
    assert _ref(conn, "CP_OUT_EC", "O12") == [70.53, 76.94, 78.42, 180.16, 83.97, 83.63]
    assert _ref(conn, "CP_OUT_FC", "O12") == [70.53, 74.29, 132.0, 55.16]
    assert _ref(conn, "CP_OUT_EC", "O20") == [1083.03, 1213.31, 1275.78, 1475.69,
                                              1388.89, 1382.06]
    assert _ref(conn, "CP_OUT_EC", "O29") == [4513.84, 5196.43, 5719.82, 7132.26,
                                              6754.38, 8226.98]


def test_bloco_auxiliar_tem_as_quarenta_configuracoes(conn):
    casos = [r[0] for r in conn.execute(
        "SELECT DISTINCT CaseKey FROM P52_ExcelReferenceValue WHERE RefSet = 'MV_AUX'")]
    assert len(casos) == 40
    assert {c for c in casos if c.startswith("SV")} == {"SV1", "SV2", "SV3", "SV4"}
    assert um(conn, "SELECT COUNT(*) FROM P52_ExcelReferenceValue "
                    "WHERE RefSet = 'MV_AUX' AND IDInd = 'O28'") == 40      # receita


def test_bev_a06_guarda_as_duas_referencias(conn):
    """Divergencia conhecida: o bloco auxiliar e a tabela de saidas nao batem."""
    saida = um(conn, "SELECT Value FROM P52_ExcelReferenceValue "
                     "WHERE RefSet = 'CP_OUT_EC' AND CaseKey = 'A06' AND IDInd = 'O11'")
    auxiliar = um(conn, "SELECT Value FROM P52_ExcelReferenceValue "
                        "WHERE RefSet = 'MV_AUX' AND CaseKey = 'A06' AND IDMP = 3")
    assert round(saida, 1) == 83.6 and round(auxiliar, 1) == 79.6


# --------------------------------------------------------------------------
# Regras (P35, P49, P53)
# --------------------------------------------------------------------------
def test_fatores_padrao_da_potencia_combinada(conn):
    f = {r[0]: tuple(r[1:]) for r in conn.execute(
        "SELECT IDVPT, FactorICE, FactorEE, IsProvisional FROM P53_CombinedPowerRule")}
    assert f == {"ICEV": (1.0, 0.0, 0), "SHEV": (0.0, 1.0, 0), "SPHEV": (0.0, 1.0, 0),
                 "BEV": (0.0, 1.0, 0), "HEV": (1.0, 1.0, 1), "PHEV": (1.0, 1.0, 1)}


def test_fatores_arbitrados_reproduzem_a_potencia_gravada(conn):
    """P = FatorICE x P_ICE + FatorEE x P_EE iguala a potencia combinada gravada."""
    linhas = conn.execute(
        "SELECT CaseKey, IDVPT, PowerICE, PowerEE, PowerCombined, FactorICE, FactorEE, "
        "FitKind FROM P56_CombinedPowerFit").fetchall()
    assert len(linhas) == 40
    for caso, pt, ice, ee, comb, k_ice, k_ee, tipo in linhas:
        assert tipo != "NoFit", caso
        assert 0 <= k_ice <= 1 and 0 <= k_ee <= 1
        assert k_ice * ice + k_ee * ee == pytest.approx(comb, rel=1e-9), caso
        if pt in ("ICEV", "BEV", "SHEV", "SPHEV"):          # pares fixos
            assert tipo == "Fixed"
            assert (k_ice, k_ee) == ((1.0, 0.0) if pt == "ICEV" else (0.0, 1.0))


def test_fatores_arbitrados_da_rodada_gravada(conn):
    """Control Panel BP12:BU12 e BF12:BI12: o que a planilha fez em cada caso."""
    f = {r[0]: r[1:] for r in conn.execute(
        "SELECT CaseKey, FactorICE, FactorEE, FitKind, RefSet FROM P56_CombinedPowerFit")}
    assert f["A02"][:3] == (1.0, 0.0, "ICE")                     # HEV: motor a combustao
    assert f["A04"][:3] == (1.0, 1.0, "Sum")                     # PHEV equalizado: soma
    assert f["A04"][3] == "CP_OUT_EC"
    assert f["SV3"][:3] == (0.0, 1.0, "EE")                      # PHEV livre: o maior e o eletrico
    assert f["SV2"][:3] == (1.0, 0.0, "ICE")


def test_phev_do_bloco_auxiliar_e_empate_e_a_divergencia_fica_anotada(conn):
    for caso in ("A14", "A24", "A34", "A44", "A54"):
        assert conn.execute("SELECT FitKind, RefSet FROM P56_CombinedPowerFit "
                            "WHERE CaseKey = ?", (caso,)).fetchone() == ("Tie", "MV_AUX")
    nota = um(conn, "SELECT NotesCPF FROM P56_CombinedPowerFit WHERE CaseKey = 'A04'")
    assert "MV_AUX" in nota and "Tie" in nota


def test_regras_de_valor_padrao(conn):
    assert um(conn, "SELECT COUNT(*) FROM P35_VehicleParamDefaultRule") == 91
    assert [r[0] for r in conn.execute(
        "SELECT IDDRV FROM P49_DefaultRuleVersion WHERE IsDefault = 1")] == ["TAB"]
    # ar-condicionado: luxo primeiro, depois o porte
    assert conn.execute("SELECT IDLR, Value FROM P35_VehicleParamDefaultRule "
                        "WHERE IDMP = 17 AND RuleSeq = 1").fetchone() == ("Luxury", 20000.0)
    # partida: 0,03 x potencia do motor a combustao
    assert conn.execute("SELECT DISTINCT Value, FactorOfIDMP FROM P35_VehicleParamDefaultRule "
                        "WHERE IDMP = 18 AND FactorOfIDMP IS NOT NULL").fetchall() == [(0.03, 2)]
    # porte: cinco faixas de area, a ultima sem teto
    assert [tuple(r) for r in conn.execute(
        "SELECT AreaMax, ValueText FROM P35_VehicleParamDefaultRule "
        "WHERE IDMP = 44 ORDER BY RuleSeq")] == [
        (6.9, "Subcompact"), (7.9, "Compact"), (8.5, "Midsize"), (10.5, "Large"),
        (None, "ExtraLarge")]


# --------------------------------------------------------------------------
# Fatores de emissao (P10, P11)
# --------------------------------------------------------------------------
def test_listas_de_fatores_da_planilha_estao_na_base(conn):
    versoes = {r[0] for r in conn.execute("SELECT IDEFV FROM P10_EFVersion")}
    assert {"G22", "G23", "G24", "BR25BR", "BR25m", "BR25GLO"} <= versoes     # as da 0.9.0
    novas = {"GLO23", "BR23", "BR23_100", "BR23_ICEV_SUV", "BR23_HEV", "BR23_PHEV", "BR23_BEV"}
    assert novas <= versoes
    n_materiais = um(conn, "SELECT COUNT(*) FROM P09_Material")
    for v in novas:
        assert um(conn, "SELECT COUNT(*) FROM P11_EmissionFactor WHERE IDEFV = ?", v) \
            == n_materiais, v
    assert um(conn, "SELECT EF FROM P11_EmissionFactor WHERE IDM = '1' AND IDEFV = 'BR23'") \
        == pytest.approx(3.0331802352941177)


# --------------------------------------------------------------------------
# Receitas de materiais (P15, P16)
# --------------------------------------------------------------------------
def test_receitas_da_rodada_gravada_estao_na_base(conn):
    """Toda receita que o bloco auxiliar da planilha nomeia existe em P15."""
    usadas = {r[0] for r in conn.execute(
        "SELECT DISTINCT ValueText FROM P52_ExcelReferenceValue "
        "WHERE RefSet = 'MV_AUX' AND IDInd = 'O28'")}
    assert len(usadas) == 13
    na_base = {r[0] for r in conn.execute("SELECT IDVMR FROM P15_VehicleMaterialRecipe")}
    assert usadas <= na_base


def test_receitas_greet_2022_a_2024_estao_na_base_e_as_da_090_ficaram(conn):
    """T:CA do M2: 10 receitas de 2022, 10 de 2023 e 36 de 2024, FCEV incluida."""
    greet = conn.execute(
        "SELECT IDVMR, IDVPT, IDVDT FROM P15_VehicleMaterialRecipe "
        "WHERE DsVMR LIKE '%do GREET 20__ (%'").fetchall()
    assert len(greet) == 56
    assert {pt for _, pt, _ in greet} == {"ICEV", "HEV", "PHEV", "BEV", "FCEV"}
    por_edicao = dict(conn.execute(
        "SELECT substr(DsVMR, instr(DsVMR, 'GREET'), 10), COUNT(*) "
        "FROM P15_VehicleMaterialRecipe WHERE DsVMR LIKE '%do GREET 20__ (%' GROUP BY 1"))
    assert por_edicao == {"GREET 2022": 10, "GREET 2023": 10, "GREET 2024": 36}
    assert um(conn, "SELECT COUNT(*) FROM P15_VehicleMaterialRecipe "
                    "WHERE DsVMR LIKE '%GREET 2024%' AND IDVPT <> 'FCEV'") == 30
    # a serie diz a classe do veiculo: G carro de passeio, S SUV, P picape
    for nome, _, carroceria in greet:
        serie = nome.split("-")[1][0]
        assert carroceria == {"G": None, "S": "SUV", "P": "PUT"}[serie], nome
    assert um(conn, "SELECT COUNT(*) FROM P15_VehicleMaterialRecipe") == 68


def test_receitas_novas_fecham_em_um_por_grupo(conn):
    """Invariante I1: em cada grupo usado, as fracoes de massa somam 1."""
    somas = conn.execute(
        "SELECT s.IDVMR, s.IDGG, SUM(s.MshareGG) FROM P16_MaterialShare s "
        "JOIN P09_Material m ON m.IDM = s.IDM AND m.ShareRole = 'material' "
        "WHERE s.IDVMR LIKE '%-%' GROUP BY 1, 2").fetchall()
    assert len({vmr for vmr, _g, _s in somas}) == 56
    for vmr, grupo, soma in somas:
        assert soma == pytest.approx(1.0, abs=1e-9) or abs(soma) < 1e-9, (vmr, grupo)


def test_nucleo_calcula_com_receita_greet(conn):
    """A receita importada e utilizavel: o ICEV da rodada gravada fecha a conta.

    Nao e ainda o teste de paridade (passo 5): a massa e o GEE ficam a menos de
    1% dos valores gravados, e a diferenca que resta esta registrada em
    docs/05a, item D6.
    """
    base = loader.load_sqlite(DB)
    gc = {int(i): (v or 0.0) for i, v in conn.execute(
        "SELECT IDMP, Value FROM P52_ExcelReferenceValue WHERE RefSet = 'MV_AUX' "
        "AND CaseKey = 'A01' AND IDMP BETWEEN 2 AND 40")}
    r = calc.calculate_vehicle(base, gc, powertrain="ICEV", battery_id=None, idmpv=1,
                               idvmr="ICEV-G21", idefv="BR23", idapv="A-EF",
                               supplied=set(gc))
    massa = um(conn, "SELECT Value FROM P52_ExcelReferenceValue WHERE RefSet = 'CP_OUT_EC' "
                     "AND CaseKey = 'A01' AND IDInd = 'O20'")
    gee = um(conn, "SELECT Value FROM P52_ExcelReferenceValue WHERE RefSet = 'CP_OUT_EC' "
                   "AND CaseKey = 'A01' AND IDInd = 'O29'")
    assert r["totals"]["MassIDV"] == pytest.approx(massa, rel=0.01)
    assert r["totals"]["GHGCradleToGate"] == pytest.approx(gee, rel=0.01)


# --------------------------------------------------------------------------
# Projeto antigo recebe os parametros da Fase A
# --------------------------------------------------------------------------
def test_projeto_da_090_recebe_os_parametros_sem_mudar_resultado(tmp_path):
    projeto = str(tmp_path / "antigo.sqlite")
    shutil.copyfile(PROJETO_090, projeto)
    antes = calc.calculate(loader.load_sqlite(projeto))
    c = sqlite3.connect(projeto)
    schema.migrate(c, project_name="Antigo")
    hash_antes = c.execute("SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'").fetchone()
    feito = schema.sync_fase_a(c, DB)
    assert feito["P26_MarketVehicle"] == 154 and feito["P10_EFVersion"] == 7
    assert feito["P12_Powertrain"] == 2 and feito["P13_DesignType"] == 2
    assert feito["P15_VehicleMaterialRecipe"] == 56 and feito["P16_MaterialShare"] == 6888
    assert c.execute("PRAGMA foreign_key_check").fetchall() == []
    assert c.execute("SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'").fetchone() \
        == hash_antes
    assert c.execute("SELECT Value FROM M00_BaseInfo WHERE Key='FaseABaseHash'").fetchone()[0] \
        == sqlite3.connect(DB).execute(
            "SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'").fetchone()[0]
    assert schema.sync_fase_a(c, DB)["P10_EFVersion"] == 0          # repetivel
    c.close()
    depois = calc.calculate(loader.load_sqlite(projeto))
    assert antes.keys() == depois.keys()
    for chave in antes:
        assert antes[chave]["totals"] == depois[chave]["totals"], chave
