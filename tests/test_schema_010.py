"""Schema 0.10 (Fase A): tabelas novas, restricoes e migracao 0.9 -> 0.10.

Passo 2 da Fase A. O que se garante aqui:

* um banco vazio e um arquivo da 0.9.0 chegam ao mesmo esquema;
* a migracao nao altera nenhum dado nem nenhum resultado existente;
* as regras que o dicionario (docs/07) atribui ao banco sao de fato do banco;
* o dicionario e o DDL descrevem as mesmas colunas.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3

import pytest

from core import calc, loader, schema

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: Um arquivo genuino da 0.9.0 (a base de referencia como publicada naquela
#: versao). E contra ele que a migracao e testada.
DB = os.path.join(REPO, "tests", "fixtures", "base_090.sqlite")
DICIONARIO = os.path.join(REPO, "docs", "07-dicionario-de-dados-fase-a.md")


# --------------------------------------------------------------------------
# Apoio
# --------------------------------------------------------------------------
@pytest.fixture()
def projeto(tmp_path):
    """Copia de um arquivo da 0.9.0, ainda sem as tabelas da 0.10."""
    destino = tmp_path / "projeto.sqlite"
    shutil.copyfile(DB, destino)
    return str(destino)


@pytest.fixture()
def migrado(projeto):
    conn = sqlite3.connect(projeto)
    schema.migrate(conn, project_name="Teste")
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


def _colunas(conn, tabela):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")]


def _semear_analise(conn):
    """O minimo para existir uma analise equalizada com um caso."""
    conn.execute("INSERT INTO P54_MarketParam (IDMP, DsMP, SheetColumn) "
                 "VALUES (2, 'ICE power', 'O')")
    conn.execute("INSERT INTO P26_MarketVehicle (IDMV, DsMV, IDVPT, IDVDT, IDVS, IDLR, "
                 "IsSelecao) VALUES (1, 'SELECAO HATCH C', 'ICEV', 'Hatchback', "
                 "'Subcompact', 'Regular', 1)")
    conn.execute("INSERT INTO P29_VehicleCategory (IDVC, DsVC, CaseDigit, IDVDT, IDVS, "
                 "IDLR, IDMVSelecao) VALUES ('A0', 'Hatch Compact Regular', 0, "
                 "'Hatchback', 'Subcompact', 'Regular', 1)")
    idmpv = conn.execute("SELECT IDMPV FROM P05_MassParamVersion").fetchone()[0]
    idapv = conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion").fetchone()[0]
    conn.execute(
        "INSERT INTO D06_Analysis (IDA, DsA, Mode, IDVC, IDMVRef, FuelScenario, TestNorm, "
        "DistanceCurve, IDEFV, IDMPV, IDAPV) VALUES (1, 'A0', 'EC', 'A0', 1, "
        "'Ethanol E100', 'NBR', 'SAE_J2841_EPA_USA', 'G24', ?, ?)", (idmpv, idapv))
    conn.commit()
    return idmpv, idapv


# --------------------------------------------------------------------------
# Um esquema so, por dois caminhos
# --------------------------------------------------------------------------
def test_banco_vazio_tem_todas_as_tabelas_da_010():
    conn = sqlite3.connect(":memory:")
    schema.create_schema(conn)
    nomes = schema.table_names(conn)
    for tabela in schema.TABLES_010 + ["R46_RunComparison"]:
        assert tabela in nomes, tabela
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migrado_e_criado_do_zero_tem_as_mesmas_colunas(migrado):
    novo = sqlite3.connect(":memory:")
    schema.create_schema(novo)
    for tabela in schema.TABLES_010 + schema.CALCULABLE_TABLES:
        assert _colunas(migrado, tabela) == _colunas(novo, tabela), tabela


def test_migracao_pode_ser_repetida(projeto):
    conn = sqlite3.connect(projeto)
    primeira = schema.migrate(conn, project_name="Teste")
    pid = conn.execute("SELECT ProjectID FROM M03_Project").fetchone()[0]
    segunda = schema.migrate(conn, project_name="Outro nome")
    assert primeira and segunda == []
    assert conn.execute("SELECT ProjectID, ProjectName FROM M03_Project").fetchall() \
        == [(pid, "Teste")]
    conn.close()


def test_migracao_recusa_arquivo_que_nao_e_projeto(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "vazio.sqlite"))
    with pytest.raises(ValueError):
        schema.migrate(conn, project_name="x")
    assert schema.table_names(conn) == set()


# --------------------------------------------------------------------------
# A migracao nao muda dado nem resultado
# --------------------------------------------------------------------------
def test_migracao_preserva_os_dados_da_090(projeto):
    antes = sqlite3.connect(DB)
    conn = sqlite3.connect(projeto)
    schema.migrate(conn, project_name="Teste")
    for tabela in schema.PARAM_TABLES + schema.SCENARIO_TABLES:
        cols = ", ".join(_colunas(antes, tabela))
        assert conn.execute(f"SELECT {cols} FROM {tabela}").fetchall() \
            == antes.execute(f"SELECT {cols} FROM {tabela}").fetchall(), tabela
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'").fetchone() \
        == antes.execute("SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'").fetchone()
    for tabela in schema.CALCULABLE_TABLES:
        assert {r[0] for r in conn.execute(f"SELECT IsCalculable FROM {tabela}")} == {1}
    conn.close()
    antes.close()


def test_migracao_nao_muda_nenhum_resultado(projeto):
    antes = calc.calculate(loader.load_sqlite(DB))
    conn = sqlite3.connect(projeto)
    schema.migrate(conn, project_name="Teste")
    conn.close()
    depois = calc.calculate(loader.load_sqlite(projeto))
    assert antes.keys() == depois.keys() and len(antes) > 0
    for chave in antes:
        assert antes[chave]["totals"] == depois[chave]["totals"], chave
        assert antes[chave]["C11"].equals(depois[chave]["C11"]), chave


def test_carregador_abre_arquivo_da_090_e_da_010(projeto):
    velho = loader.load_sqlite(projeto)
    assert "D06" not in velho and "P30" not in velho
    conn = sqlite3.connect(projeto)
    schema.migrate(conn, project_name="Teste")
    conn.close()
    novo = loader.load_sqlite(projeto)
    for curto in ("P26", "P30", "P53", "D06", "D07", "D09", "D12", "R45", "M03"):
        assert curto in novo, curto
    assert len(novo["M03"]) == 1


def test_base_de_referencia_migrada_nao_ganha_identidade(projeto):
    conn = sqlite3.connect(projeto)
    schema.migrate(conn)
    assert conn.execute("SELECT COUNT(*) FROM M03_Project").fetchone()[0] == 0
    conn.close()


# --------------------------------------------------------------------------
# Identidade do projeto (M03)
# --------------------------------------------------------------------------
def test_id_do_projeto_e_neutro_e_bem_formado():
    ids = {schema.new_project_id() for _ in range(200)}
    assert len(ids) == 200
    assert all(re.fullmatch(r"PRJ-[A-HJ-NP-Z2-9]{8}", i) for i in ids)


def test_projeto_tem_uma_linha_so(migrado):
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute(
            "INSERT INTO M03_Project (ProjectID, ProjectName, CreatedAt, SchemaVersion) "
            "VALUES ('PRJ-ABCDEFGH', 'segundo', '2026-11-16T00:00:00', '0.10')")


def test_id_fora_do_formato_e_recusado(migrado):
    migrado.execute("DELETE FROM M03_Project")
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute(
            "INSERT INTO M03_Project (ProjectID, ProjectName, CreatedAt, SchemaVersion) "
            "VALUES ('psplima_20261115a', 'x', '2026-11-16T00:00:00', '0.10')")


# --------------------------------------------------------------------------
# Regras que o dicionario atribui ao banco
# --------------------------------------------------------------------------
def test_analise_equalizada_exige_categoria_e_referencia(migrado):
    idmpv, idapv = _semear_analise(migrado)
    base = ("INSERT INTO D06_Analysis (IDA, DsA, Mode, IDVC, IDMVRef, FuelScenario, "
            "TestNorm, DistanceCurve, IDEFV, IDMPV, IDAPV) VALUES "
            "(?, 'x', ?, ?, ?, 'Ethanol E100', 'NBR', 'c', 'G24', ?, ?)")
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute(base, (2, "EC", None, None, idmpv, idapv))
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute(base, (3, "FC", "A0", 1, idmpv, idapv))
    migrado.execute(base, (4, "FC", None, None, idmpv, idapv))


def test_padroes_da_analise_sao_os_decididos(migrado):
    _semear_analise(migrado)
    assert migrado.execute(
        "SELECT CombinedPowerRule, ParamProfile, AnalysisType, Boundary FROM D06_Analysis"
    ).fetchone() == ("Default", "Expert", "GHG_LCA_LCC", "MAT_ASM")


def test_caso_aponta_para_veiculo_e_alternativa_que_existem(migrado):
    _semear_analise(migrado)
    idv, idea = migrado.execute(
        "SELECT IDV, IDEA FROM D02_EvaluationAlternative LIMIT 1").fetchone()
    caso = ("INSERT INTO D07_AnalysisVehicle (IDA, IDCase, CaseKey, CaseRole, IDVPT, IDV, "
            "IDEA, SizingOrigin) VALUES (1, ?, ?, 'REF', 'ICEV', ?, ?, 'ExcelReference')")
    migrado.execute(caso, (1, "A01", idv, idea))
    with pytest.raises(sqlite3.IntegrityError):          # oitavo caso
        migrado.execute(caso, (8, "A08", idv, idea))
    with pytest.raises(sqlite3.IntegrityError):          # rotulo repetido
        migrado.execute(caso, (2, "A01", idv, idea))
    with pytest.raises(sqlite3.IntegrityError):          # veiculo inexistente
        migrado.execute(caso, (3, "A03", 999999, 1))


def test_parametro_alterado_tem_um_valor_e_uma_origem(migrado):
    _semear_analise(migrado)
    migrado.execute("INSERT INTO P30_ControlParam (IDCP, Cell, Section, Level, DsCP) "
                    "VALUES ('X23', 'Z23', 'UPP', 'B', 'BEV AER')")
    linha = ("INSERT INTO D08_ControlParamValue (IDA, IDCP, Profile, Value, ValueText, "
             "ValueSource, UpdatedAt) VALUES (1, 'X23', ?, ?, ?, ?, '2026-11-16')")
    migrado.execute(linha, ("Expert", 350.0, None, "estudo do autor"))
    migrado.execute(linha, ("Basic", 300.0, None, "estudo do autor"))   # perfil proprio
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute(linha, ("Expanded", 350.0, "texto", "x"))       # dois valores
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute(linha, ("Expanded", 350.0, None, "  "))         # sem origem


def test_ajuste_da_potencia_combinada_e_por_caso_e_entre_zero_e_um(migrado):
    _semear_analise(migrado)
    idv, idea = migrado.execute(
        "SELECT IDV, IDEA FROM D02_EvaluationAlternative LIMIT 1").fetchone()
    migrado.execute(
        "INSERT INTO D07_AnalysisVehicle (IDA, IDCase, CaseKey, CaseRole, IDVPT, IDV, "
        "IDEA, SizingOrigin) VALUES (1, 2, 'A02', 'EQ', 'HEV', ?, ?, 'ExcelReference')",
        (idv, idea))
    ajuste = ("INSERT INTO D12_CombinedPowerOverride (IDA, IDCase, FactorICE, FactorEE) "
              "VALUES (1, ?, ?, ?)")
    migrado.execute(ajuste, (2, 1.0, 0.4))
    with pytest.raises(sqlite3.IntegrityError):          # um ajuste por caso
        migrado.execute(ajuste, (2, 1.0, 0.5))
    with pytest.raises(sqlite3.IntegrityError):          # fator acima de 1
        migrado.execute(ajuste.replace("1, ?", "1, 3"), (1.5, 0.5))
    with pytest.raises(sqlite3.IntegrityError):          # fator negativo
        migrado.execute(ajuste.replace("1, ?", "1, 3"), (-0.1, 0.5))
    with pytest.raises(sqlite3.IntegrityError):          # caso que nao existe
        migrado.execute(ajuste, (5, 1.0, 1.0))


def test_rodada_e_resultado_ficam_gravados_e_ligados(migrado):
    _semear_analise(migrado)
    migrado.execute("INSERT INTO M01_RunMetadata VALUES ('r1', '2026-11-16', '0.10.0', "
                    "'h', 'Teste', 'OK')")
    migrado.execute(
        "INSERT INTO D09_Run (RunID, IDA, RunSeq, FrozenAt, InputSnapshot, InputHash, "
        "ParamBaseHash, ReferenceWorkbook, CalculatorVersion) VALUES ('r1', 1, 1, "
        "'2026-11-16', '{}', ?, 'h', 'LCA_LV_i3ET_20261101.xlsx', '0.10.0')", ("a" * 64,))
    migrado.execute("INSERT INTO P51_OutputIndicator (IDInd, DsInd, utInd, PanelRow) "
                    "VALUES ('O20', 'Vehicle weight', 'kg', 20)")
    migrado.execute("INSERT INTO R45_PowertrainSummary (RunID, CaseKey, IDVPT, IDInd, "
                    "Value, ValueOrigin) VALUES ('r1', 'A01', 'ICEV', 'O20', 1083.026, "
                    "'Calculated')")
    assert migrado.execute(
        "SELECT RunSeq, CaseKey, DsInd, Value, ValueOrigin FROM R46_RunComparison"
    ).fetchall() == [(1, "A01", "Vehicle weight", 1083.026, "Calculated")]
    with pytest.raises(sqlite3.IntegrityError):          # selo fora do dominio
        migrado.execute("INSERT INTO R45_PowertrainSummary (RunID, CaseKey, IDVPT, IDInd, "
                        "Value, ValueOrigin) VALUES ('r1', 'A02', 'HEV', 'O20', 1.0, 'Guess')")
    with pytest.raises(sqlite3.IntegrityError):          # rodada sem execucao em M01
        migrado.execute(
            "INSERT INTO D09_Run (RunID, IDA, RunSeq, FrozenAt, InputSnapshot, InputHash, "
            "ParamBaseHash, ReferenceWorkbook, CalculatorVersion) VALUES ('r9', 1, 2, "
            "'2026-11-16', '{}', ?, 'h', 'w', '0.10.0')", ("a" * 64,))


def test_valor_de_referencia_do_excel_diz_de_onde_veio(migrado):
    _semear_analise(migrado)
    migrado.execute("INSERT INTO P51_OutputIndicator (IDInd, DsInd) VALUES ('O20', 'w')")
    ref = ("INSERT INTO P52_ExcelReferenceValue (RefSet, CaseKey, IDInd, IDMP, Value, "
           "Workbook, Sheet, Cell) VALUES (?, 'A01', ?, ?, 1.0, 'w.xlsx', 's', 'BP20')")
    migrado.execute(ref, ("CP_OUT_EC", "O20", None))
    migrado.execute(ref, ("MV_AUX", None, 2))
    with pytest.raises(sqlite3.IntegrityError):          # indicador e parametro juntos
        migrado.execute(ref, ("MV_AUX", "O20", 2))
    with pytest.raises(sqlite3.IntegrityError):          # repetido
        migrado.execute(ref, ("CP_OUT_EC", "O20", None))


def test_fatores_padrao_de_potencia_tem_uma_linha_por_motorizacao(migrado):
    migrado.execute("INSERT INTO P53_CombinedPowerRule (IDVPT, FactorICE, FactorEE, "
                    "IsProvisional) VALUES ('HEV', 1, 1, 1)")
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute("INSERT INTO P53_CombinedPowerRule (IDVPT, FactorICE, FactorEE, "
                        "IsProvisional) VALUES ('HEV', 1, 0, 1)")
    with pytest.raises(sqlite3.IntegrityError):
        migrado.execute("INSERT INTO P53_CombinedPowerRule (IDVPT, FactorICE, FactorEE, "
                        "IsProvisional) VALUES ('PHEV', 2, 0, 1)")


# --------------------------------------------------------------------------
# O dicionario e o DDL dizem a mesma coisa
# --------------------------------------------------------------------------
def test_dicionario_e_ddl_tem_as_mesmas_colunas():
    """Cada tabela da 0.10 tem, no dicionario, as colunas do banco, na ordem."""
    with open(DICIONARIO, encoding="utf-8") as fh:
        texto = fh.read()
    conn = sqlite3.connect(":memory:")
    schema.create_schema(conn)
    for tabela in schema.TABLES_010:
        m = re.search(rf"^### .*`{tabela}`.*?\n(.*?)(?=^### |^## |\Z)", texto, re.S | re.M)
        assert m, f"{tabela} sem secao no dicionario"
        documentadas = re.findall(r"^\| `(\w+)` \|", m.group(1), re.M)
        assert documentadas == _colunas(conn, tabela), tabela
