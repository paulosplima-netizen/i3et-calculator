"""B2 -- dados de mercado: leitura dos informativos, correspondencia com o catalogo e C33."""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

from core import market_data as md
from core import schema

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")

INFORMATIVO = """
            Ranking dos emplacamentos acumulados até Dezembro/2025

       AUTOMÓVEIS                                  COMERCIAIS LEVES

      1º            VW/POLO             122.672   1º         FIAT/STRADA           142.891
      2º            FIAT/ARGO           102.630   2º         VW/SAVEIRO             67.752
      3º     M.BENZ/SPRINTER 417          693   3º       RAM/3500.0               1.406

            Ranking dos emplacamentos em Dezembro/2025

      1º            VW/POLO               9.381   1º         FIAT/STRADA            9.000
"""


@pytest.fixture(scope="module")
def conn():
    c = sqlite3.connect(DB)
    yield c
    c.close()


def test_normalizacao_e_chave():
    assert md.norm("  Hilux  sw4 ") == "HILUX SW4"
    assert md.norm("3500.0") == "3500"
    assert md.match_key("M.BENZ", "Sprinter") == "MERCEDES-BENZ/SPRINTER"
    assert md.match_key("RAM", "3500.0") == "RAM/3500"
    assert md.match_key("FORD", "F-150") == md.match_key("FORD", "F150")
    assert md.split_make_model("OMODA JAECOO/JAECOO 7") == ("OMODA JAECOO", "JAECOO 7")


def test_grupo_de_combustivel():
    assert [md.fuel_group(f) for f in ("Flex", "Gasoline", "Diesel", "Electricity")] \
        == ["EG", "EG", "D", "X"]


def test_informativo_fenabrave_duas_colunas_e_dois_quadros():
    secoes = md.parse_fenabrave_text(INFORMATIVO)
    assert [(s.kind, s.period_end, len(s.rows)) for s in secoes] == [
        ("YTD", "2025-12", 6), ("Month", "2025-12", 2)]
    ytd = md.adopted_section(secoes)
    assert ytd.kind == "YTD"
    por = {(r.sales_class, r.ranking): r for r in ytd.rows}
    assert por[("V", 1)].units == 122672 and por[("CL", 1)].units == 142891
    assert por[("V", 3)].model == "SPRINTER 417" and por[("V", 3)].units == 693
    assert por[("CL", 3)].key == "RAM/3500" and por[("CL", 3)].units == 1406


def test_campos_do_pbev_iguais_aos_da_ferramenta():
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import import_pbev
    esperado = [nome for letra, nome in import_pbev.FIELDS.items() if letra != "C"]
    assert md.PBEV_FIELD_NAMES == esperado


def test_linhas_do_pbev():
    linha = ["Compacto", "Fiat", "Argo", "DRIVE 1.0", "1.0-12V", "Combustão", "CVT", "S", "E",
             "F", "20", "201"] + ["x"] * 14
    linha[9] = "ND"
    r = md.parse_pbev_rows([["Categoria", "Marca"] + [""] * 30, linha, ["", "", ""]])
    assert len(r) == 1 and r[0].key == "FIAT/ARGO"
    assert r[0].fields["Motor"] == "1.0-12V" and r[0].fields["DirecaoAssistida"] == "E"
    assert md.duplicate_keys(r + r) and not md.duplicate_keys(r)


def test_tabelas_do_b2_na_base(conn):
    for t in schema.TABLES_012:
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] > 0
    assert conn.execute("SELECT COUNT(*) FROM P47_MarketSales").fetchone()[0] == 111
    assert conn.execute("SELECT COUNT(*) FROM P47_MarketSales WHERE IDMV IS NULL"
                        ).fetchone()[0] == 0
    # unidades adotadas = as que a Market Vehicles usa (P26.SalesUnits)
    dif = conn.execute("SELECT COUNT(*) FROM P47_MarketSales s JOIN P26_MarketVehicle v "
                       "USING (IDMV) WHERE s.UnitsAdopted <> v.SalesUnits").fetchone()[0]
    assert dif == 0
    assert set(schema.TABLES_012) <= set(schema.EDITORIAL_TABLES)


def test_correspondencia_com_o_catalogo(conn):
    sec = md.adopted_section(md.parse_fenabrave_text(INFORMATIVO))
    res = {m.row.key: m for m in md.match_to_catalog(conn, sec.rows)}
    assert res["VW/POLO"].status == "exact" and res["VW/POLO"].idmvs == [17]
    assert res["FIAT/ARGO"].status == "exact"
    assert res["MERCEDES-BENZ/SPRINTER 417"].status == "exact"
    ausente = md.match_to_catalog(conn, [md.SalesRow("V", 9, "OMODA JAECOO", "JAECOO 7", 4919)])
    assert ausente[0].status == "none"


def test_modelo_dividido_por_motorizacao(conn):
    # O informativo traz HR-V com 61.227; o catalogo tem HR-V (60.577) + HR-V HEV (650).
    r = md.SalesRow("V", 9, "HONDA", "HR-V", 61227)
    m = md.match_to_catalog(conn, [r])[0]
    assert m.status == "split" and len(m.idmvs) == 2 and m.catalog_units == 61227
    # com a redistribuicao ainda nao feita, o master ve a divergencia
    r2 = md.SalesRow("V", 9, "HONDA", "HR-V", 70000)
    assert md.match_to_catalog(conn, [r2])[0].status == "differs"


def test_referencia_ponderada_c33_igual_a_planilha(conn):
    """C33: as medias ponderadas por segmento reproduzem os 60 valores `Avg` da planilha,
    inclusive a area frontal derivada (0,85 x largura x altura)."""
    total = 0
    for idvc, idsel in conn.execute("SELECT IDVC, IDMVSelecao FROM P29_VehicleCategory"):
        ref = md.reference_params(conn, idvc)
        esperado = dict(conn.execute("SELECT IDMP, Value FROM P27_MarketVehicleParam "
                                     "WHERE IDMV = ? AND ValueClass = 'Avg'", (idsel,)))
        assert set(ref) == set(esperado)
        for p, v in esperado.items():
            assert ref[p] == pytest.approx(v, rel=1e-6), (idvc, p)
            total += 1
    assert total == 60


def test_c33_responde_as_unidades(conn):
    """Trocar as unidades muda a media; unidades iguais as da base nao."""
    base = md.reference_params(conn, "A0")
    mesmas = dict(conn.execute("SELECT IDMV, SalesUnits FROM P26_MarketVehicle"))
    assert md.reference_params(conn, "A0", mesmas) == base
    dobra = {i: (u * 2 if i == 8 else u) for i, u in mesmas.items()}      # FIAT ARGO
    assert md.reference_params(conn, "A0", dobra)[2] != base[2]


def test_cobertura_contra_o_total_da_anfavea(conn):
    total = conn.execute("SELECT Units FROM P60_FleetLicensingTotal WHERE RefYear = 2025"
                         ).fetchone()[0]
    cob = md.segment_coverage(conn, total)
    assert total == 2424281
    assert cob["share"] == pytest.approx(0.82866, abs=1e-4)      # Market Vehicles L226
