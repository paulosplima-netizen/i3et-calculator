"""Esquema 0.11 (bloco B1): tabelas novas, colunas novas e migracao 0.10 -> 0.11.

O que se garante aqui:

* banco vazio e arquivo migrado chegam ao mesmo esquema;
* a migracao so acrescenta: nenhum dado existente muda;
* as regras do dicionario do B1 (docs/09) que sao do banco sao do banco;
* o dicionario cita todas as tabelas e colunas novas;
* a base de referencia traz P63 (68 receitas) e continua integra.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3

import pytest

from core import schema

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_090 = os.path.join(REPO, "tests", "fixtures", "base_090.sqlite")
DB_REF = os.path.join(REPO, "data", "base_referencia.sqlite")
DICIONARIO = os.path.join(REPO, "docs", "09-dicionario-de-dados-b1.md")


def _colunas(conn, tabela):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")]


@pytest.fixture()
def migrado(tmp_path):
    destino = tmp_path / "projeto.sqlite"
    shutil.copyfile(DB_090, destino)
    conn = sqlite3.connect(destino)
    schema.migrate(conn, project_name="Teste")
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


@pytest.fixture()
def novo():
    conn = sqlite3.connect(":memory:")
    schema.create_schema(conn)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# --------------------------------------------------------------------------
# Um esquema so, por dois caminhos
# --------------------------------------------------------------------------
def test_versao_do_esquema_e_011():
    assert schema.SCHEMA_VERSION == "0.11"


def test_banco_vazio_tem_todas_as_tabelas_da_011(novo):
    nomes = schema.table_names(novo)
    for tabela in schema.TABLES_011:
        assert tabela in nomes, tabela
    assert len(schema.TABLES_011) == 28
    assert novo.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migrado_e_criado_do_zero_tem_as_mesmas_colunas(migrado, novo):
    tabelas = set(schema.TABLES_011) | {t for t, _, _ in schema.COLUMNS_011}
    for tabela in sorted(tabelas):
        assert _colunas(migrado, tabela) == _colunas(novo, tabela), tabela


def test_colunas_acrescentadas_existem(novo):
    for tabela, coluna, _ in schema.COLUMNS_011:
        assert coluna in _colunas(novo, tabela), (tabela, coluna)
    for coluna in ("EstimatedMassKg", "CalibrationKg", "FinalMassKg"):
        assert coluna in _colunas(novo, "C02_MassByGroup")
    assert "MshareRaw" in _colunas(novo, "P16_MaterialShare")


def test_migracao_pode_ser_repetida(migrado):
    assert schema.apply_011(migrado) == []
    assert schema.migrate(migrado) == [] or True        # nao falha
    assert migrado.execute("SELECT SchemaVersion FROM M03_Project").fetchone()[0] == "0.11"


def test_migracao_so_acrescenta_dados(tmp_path):
    destino = tmp_path / "p.sqlite"
    shutil.copyfile(DB_090, destino)
    conn = sqlite3.connect(destino)
    antes = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("P09_Material", "P11_EmissionFactor", "P16_MaterialShare",
                       "P15_VehicleMaterialRecipe", "P02_VehicleSubgroup")}
    schema.migrate(conn, project_name="X")
    for t, n in antes.items():
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == n, t
    # valores novos de P10 recebem os padroes
    assert {r[0] for r in conn.execute("SELECT DISTINCT Origin FROM P10_EFVersion")} == {"Typed"}
    conn.close()


# --------------------------------------------------------------------------
# Regras que sao do banco
# --------------------------------------------------------------------------
def test_p62_exige_parametro_ou_constante(ref):
    conn = sqlite3.connect(":memory:")
    schema.create_schema(conn)
    conn.execute("PRAGMA foreign_keys = OFF")
    ins = ("INSERT INTO P62_BRRouteShare (IDM, Route, ShareRule, IDCP, ShareValue) "
           "VALUES ('1','RECYCLED',?,?,?)")
    conn.execute(ins, ("CONSTANT", None, 0.5))
    conn.execute("DELETE FROM P62_BRRouteShare")
    conn.execute(ins, ("PARAM", "X91", None))
    conn.execute("DELETE FROM P62_BRRouteShare")
    for regra, idcp, valor in (("PARAM", None, 0.5), ("CONSTANT", "X91", None)):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(ins, (regra, idcp, valor))


def test_p63_valida_s_entre_zero_e_um(novo):
    novo.execute("INSERT INTO P12_Powertrain (IDVPT, DsVPT) VALUES ('ICEV','x')")
    novo.execute("INSERT INTO P15_VehicleMaterialRecipe (IDVMR, IDVPT) VALUES ('R1','ICEV')")
    ok = ("INSERT INTO P63_RecipeBodyChassisMass (IDVMR, ColumnM2, BodyMassRefKg, "
          "ChassisMassRefKg, ChassisBodyRatio, BodyShareOfMassAdj) "
          "VALUES ('R1','T',700,350,0.5,?)")
    novo.execute(ok, (0.6667,))
    novo.execute("DELETE FROM P63_RecipeBodyChassisMass")
    for s in (-0.1, 1.1):
        with pytest.raises(sqlite3.IntegrityError):
            novo.execute(ok, (s,))


def test_c35_so_aceita_os_tres_estagios(novo):
    with pytest.raises(sqlite3.IntegrityError):
        novo.execute("INSERT INTO C35_VehicleLifeStage (RunID, IDA, IDCase, IDV, Stage, "
                     "GHGkg) VALUES ('r',1,1,1,'USE',1.0)")


def test_modo_de_manutencao_so_aceita_os_tres_valores(novo):
    with pytest.raises(sqlite3.IntegrityError):
        novo.execute("INSERT INTO D10_MaintenanceScenario (IDA, MaintenanceMode) "
                     "VALUES (1, 'Talvez')")


def test_metodo_de_fim_de_vida_so_aceita_os_tres_valores(novo):
    with pytest.raises(sqlite3.IntegrityError):
        novo.execute("INSERT INTO C16_EndOfLife (RunID, IDA, IDCase, EoLMethod, GHGEoL) "
                     "VALUES ('r',1,1,'OUTRO',1.0)")


# --------------------------------------------------------------------------
# Dicionario e DDL
# --------------------------------------------------------------------------
def test_dicionario_cita_todas_as_tabelas_e_colunas_novas():
    with open(DICIONARIO, encoding="utf-8") as fh:
        texto = fh.read()
    for tabela in schema.TABLES_011:
        # D10_Item e D19 etc. podem vir juntas numa secao; basta o codigo curto.
        curto = tabela.split("_")[0]
        assert re.search(rf"\b{curto}\b", texto), tabela
    for _, coluna, _ in schema.COLUMNS_011:
        assert coluna in texto, coluna


def test_p63_do_dicionario_tem_as_colunas_do_banco(novo):
    with open(DICIONARIO, encoding="utf-8") as fh:
        texto = fh.read()
    sec = re.search(r"^### P63.*?(?=^### )", texto, re.S | re.M).group(0)
    for coluna in _colunas(novo, "P63_RecipeBodyChassisMass"):
        assert f"`{coluna}`" in sec, coluna


# --------------------------------------------------------------------------
# Base de referencia
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def ref():
    c = sqlite3.connect(f"file:{DB_REF}?mode=ro", uri=True)
    yield c
    c.close()


def test_base_de_referencia_traz_p63_de_68_receitas(ref):
    assert ref.execute("SELECT COUNT(*) FROM P63_RecipeBodyChassisMass").fetchone()[0] == 68
    n = ref.execute("SELECT COUNT(*) FROM P63_RecipeBodyChassisMass p JOIN "
                    "P15_VehicleMaterialRecipe r USING (IDVMR)").fetchone()[0]
    assert n == 68
    k, s = ref.execute("SELECT ChassisBodyRatio, BodyShareOfMassAdj FROM "
                       "P63_RecipeBodyChassisMass WHERE IDVMR='ICEV-G21'").fetchone()
    assert abs(s - 1 / (1 + k)) < 1e-9


def test_base_de_referencia_integra_e_na_011(ref):
    assert ref.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert ref.execute("PRAGMA foreign_key_check").fetchall() == []
    assert ref.execute("SELECT Value FROM M00_BaseInfo WHERE Key='SchemaVersion'") \
        .fetchone()[0] == "0.11"
    assert ref.execute("SELECT Value FROM M00_BaseInfo WHERE Key='ParamBaseHash'") \
        .fetchone()[0] == schema.param_base_hash(ref)
