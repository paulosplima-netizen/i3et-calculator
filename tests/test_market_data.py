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


def test_cobertura_contra_o_total_da_fenabrave(conn):
    """O total de mercado do modelo e o da FENABRAVE (Reference Vehicles!R20), nao o 50+50."""
    total = conn.execute("SELECT Units FROM P60_FleetLicensingTotal WHERE SourceName = "
                         "'FENABRAVE' AND RefYear = 2025 AND VehicleClass = 'LightVehicles'"
                         ).fetchone()[0]
    assert total == 2549462
    cob = md.segment_coverage(conn, total)
    assert cob["units"] == 2008914                   # Reference Vehicles!K16
    assert cob["share"] == pytest.approx(2008914 / 2549462)
    rank = conn.execute("SELECT SUM(UnitsAdopted) FROM P47_MarketSales").fetchone()[0]
    assert rank == 2424281                           # soma dos rankings 50+50 (R18)


# ---------------------------------------------------------------- B2b (22/11/2026)
ANUARIO = """
 2.2.1 Emplacamento de autoveículos - 2016–2025
   ANO   AUTOMÓVEIS COMERCIAIS LEVES CAMINHÕES ÔNIBUS TOTAL
   2024  1.948.681   538.940   124.848   22.435   2.634.904
   2025  1.997.264   554.937   113.479   23.954   2.689.634
   2026  1.000.000   1.000.000   1.000   1.000   9.999
 FONTE / SOURCE: Anfavea
"""


def test_anfavea_le_a_tabela_e_descarta_linha_que_nao_fecha():
    t = md.parse_anfavea_table(ANUARIO, "2.2.1 Emplacamento")
    assert sorted(t) == [2024, 2025]                  # 2026: soma != total
    assert t[2025] == (1997264, 554937, 113479, 23954, 2689634)


def test_anfavea_tolera_arredondamento_da_fonte():
    txt = "1.11 Estimativa\n 2016  37.389.791  5.332.763  2.014.850  385.311  45.122.716\n"
    assert md.parse_anfavea_table(txt, "1.11 Estimativa")[2016][4] == 45122716


def test_p60_guarda_a_edicao_e_vale_a_mais_recente(conn):
    adotado = dict(((a, c), (ed, u)) for ed, a, c, u in conn.execute(
        "SELECT SourceEdition, RefYear, VehicleClass, Units FROM P60_FleetLicensingTotal "
        "WHERE SourceName = 'ANFAVEA' AND IsAdopted = 1"))
    assert adotado[(2025, "Automobiles")] == ("Anuario ANFAVEA 2026", 1997264)
    assert adotado[(2024, "LightCommercials")][0] == "Anuario ANFAVEA 2026"
    assert adotado[(1957, "Automobiles")] == ("Anuario ANFAVEA 2025", 9478)
    # a mesma serie existe nas duas edicoes e so uma esta adotada
    n = conn.execute("SELECT COUNT(*) FROM P60_FleetLicensingTotal WHERE SourceName='ANFAVEA' "
                     "AND RefYear = 2024 AND VehicleClass = 'Total'").fetchone()[0]
    assert n == 2
    for _ano, _cls in [(2024, "Total")]:
        assert conn.execute("SELECT SUM(IsAdopted) FROM P60_FleetLicensingTotal WHERE "
                            "SourceName='ANFAVEA' AND RefYear=2024 AND VehicleClass='Total'"
                            ).fetchone()[0] == 1


def test_p71_frota_estimada_revisada_entre_edicoes(conn):
    v = dict(((ed, a), u) for ed, a, u in conn.execute(
        "SELECT SourceEdition, RefYear, Units FROM P71_FleetEstimate WHERE VehicleClass = "
        "'Automobiles' AND RefYear = 2016"))
    assert v[("Anuario ANFAVEA 2025", 2016)] == 37279361
    assert v[("Anuario ANFAVEA 2026", 2016)] == 37389791
    adotado = conn.execute("SELECT Units FROM P71_FleetEstimate WHERE RefYear = 2016 AND "
                           "VehicleClass = 'Automobiles' AND IsAdopted = 1").fetchone()[0]
    assert adotado == 37389791


def test_pivot_design_x_motorizacao_reproduz_a_planilha(conn):
    piv = md.design_powertrain_pivot(conn, "FEN2025")
    assert sum(piv.values()) == 2424281
    assert piv[("HATCH C", "BEV")] == 47675 and piv[("SUV ML", "PHEV")] == 69843
    assert piv[("Other", "ICEV")] == 93768
    assert sum(u for (_g, p), u in piv.items() if p == "ICEV") == 2213897


def test_largest_remainder_fecha_o_total():
    assert md.largest_remainder(10, [1, 1, 1]) == [4, 3, 3]
    assert sum(md.largest_remainder(61227, [60577, 650])) == 61227
    assert md.largest_remainder(5, [0, 0]) == [0, 0]


def _linhas_hrv():
    return [md.SalesRow("V", 9, "HONDA", "HR-V", 61227)]


def test_divisao_usa_a_edicao_anterior_e_fecha_com_o_informativo(conn):
    linhas = _linhas_hrv()
    res = md.match_to_catalog(conn, linhas)
    sp = md.split_candidates(conn, res, linhas, "FEN2025")
    assert sorted(x.powertrain for x in sp) == ["HEV", "ICEV"]
    assert {x.method for x in sp} == {"Previous"}
    assert sum(x.units for x in sp) == 61227 and md.validate_split(sp) == []
    icev = next(x for x in sp if x.powertrain == "ICEV")
    assert icev.units == 60577 and icev.pbev is not None      # candidatas visiveis ao master


def test_divisao_sem_edicao_anterior_cai_no_pbev(conn):
    linhas = _linhas_hrv()
    sp = md.split_candidates(conn, md.match_to_catalog(conn, linhas), linhas, None)
    assert {x.method for x in sp} <= {"PBEV", "Base"}
    assert sum(x.units for x in sp) == 61227


def test_master_digita_e_a_soma_precisa_fechar(conn):
    linhas = _linhas_hrv()
    sp = md.split_candidates(conn, md.match_to_catalog(conn, linhas), linhas, "FEN2025")
    icev = next(x for x in sp if x.powertrain == "ICEV")
    md.apply_master_units(sp, {icev.idmv: 60000})
    assert icev.method == "Master" and md.validate_split(sp) != []


def test_grava_a_edicao_numa_copia_e_recusa_duplicata(conn, tmp_path):
    copia = tmp_path / "b.sqlite"
    destino = sqlite3.connect(copia)
    conn.backup(destino)
    destino.execute("PRAGMA foreign_keys = ON")
    linhas = [md.SalesRow("V", 1, "VW", "POLO", 100000),
              md.SalesRow("V", 9, "HONDA", "HR-V", 61227)]
    sp = md.split_candidates(destino, md.match_to_catalog(destino, linhas), linhas, "FEN2025")
    sec = md.SalesSection("YTD", "2026-03", "Ranking dos emplacamentos acumulados até Março/2026")
    assert md.save_edition(destino, "FEN2026_03", sec, sp, "teste.pdf") == len(sp)
    assert destino.execute("SELECT COUNT(*) FROM P47_MarketSales WHERE IDMSE='FEN2026_03'"
                           ).fetchone()[0] == len(sp)
    with pytest.raises(ValueError, match="ja existe"):
        md.save_edition(destino, "FEN2026_03", sec, sp, "teste.pdf")
    destino.close()


def test_exportacao_xlsx_da_comparacao(conn, tmp_path):
    out = tmp_path / "c.xlsx"
    md.export_reference_xlsx(conn, str(out))
    from openpyxl import load_workbook
    wb = load_workbook(out)
    assert wb.sheetnames == ["Reference parameters", "Units used"]
    assert wb["Reference parameters"].max_row == 61              # cabecalho + 60 parametros


def test_p72_motorizacao_anuario_2026(conn):
    def u(tab, cls, cat, ano=2025):
        return conn.execute(
            "SELECT Units FROM P72_FleetLicensingByPowertrain WHERE SourceTable=? AND "
            "VehicleClass=? AND Category=? AND RefYear=?", (tab, cls, cat, ano)).fetchone()[0]
    assert u("2.2.8", "Automobiles", "FlexFuel") == 1592071
    assert u("2.2.8", "LightCommercials", "Diesel") == 228019
    assert u("2.2.9", "Automobiles", "BEV") == 79714
    assert u("2.2.9", "Automobiles", "PHEV") == 94147
    assert u("2.2.10", "Automobiles", "Upto1000cc") == 1078308
    # 2.2.8: combustiveis somam o total da ANFAVEA (automoveis 1.997.264)
    tot = conn.execute("SELECT SUM(Units) FROM P72_FleetLicensingByPowertrain WHERE "
                       "SourceTable='2.2.8' AND VehicleClass='Automobiles' AND RefYear=2025"
                       ).fetchone()[0]
    assert tot == 1997264
    # 2.2.9 abre exatamente a coluna Electrified da 2.2.8
    eletr = sum(u("2.2.9", "Automobiles", c) for c in
                ("BEV", "FlexHybrid", "GasolineHybrid", "DieselHybrid", "PHEV"))
    assert eletr == u("2.2.8", "Automobiles", "Electrified") == 282895


def test_p72_serie_historica_do_i3ef(conn):
    def u(ano, cls, dim, cat):
        return conn.execute(
            "SELECT Units, IsAdopted FROM P72_FleetLicensingByPowertrain WHERE SourceName='i3EF' "
            "AND RefYear=? AND VehicleClass=? AND Dimension=? AND Category=?",
            (ano, cls, dim, cat)).fetchone()
    assert u(1957, "Automobiles", "Fuel", "Gasoline") == (9478, 1)   # antes de 2016 vale o i3EF
    assert u(2025, "Automobiles", "Fuel", "Gasoline") == (79039, 0)  # 2016+: so comparacao
    anos = conn.execute("SELECT MIN(RefYear), MAX(RefYear) FROM P72_FleetLicensingByPowertrain "
                        "WHERE SourceName='i3EF'").fetchone()
    assert anos == (1957, 2025)
    # HEV+PHEV+BEV do i3EF fecham com a coluna Electrified (decisao 25)
    for ano in (1990, 2020, 2025):
        el = conn.execute("SELECT SUM(Units) FROM P72_FleetLicensingByPowertrain WHERE "
                          "SourceName='i3EF' AND RefYear=? AND VehicleClass='Automobiles' "
                          "AND Dimension='Electrified'", (ano,)).fetchone()[0]
        assert el == u(ano, "Automobiles", "Fuel", "Electrified")[0]


def test_segmentos_editaveis_e_restauracao(conn):
    import shutil
    import sqlite3
    import tempfile
    tmp = tempfile.mkdtemp() + "/b.sqlite"
    shutil.copy(conn.execute("PRAGMA database_list").fetchone()[2], tmp)
    c = sqlite3.connect(tmp)
    antes = md.reference_params(c, "A0")
    n = c.execute("SELECT COUNT(*) FROM P70_ReferenceSegment WHERE IDVC='A0'").fetchone()[0]
    md.save_segments(c, "A0", [{"IDVDT": "Hatchback", "IDVS": "Compact", "FuelGroup": "EG",
                                "IDVPT": "ICEV"}])
    assert c.execute("SELECT COUNT(*) FROM P70_ReferenceSegment WHERE IDVC='A0' AND "
                     "Origin='Master'").fetchone()[0] == 1
    assert md.reference_params(c, "A0") != antes
    with pytest.raises(ValueError):
        md.save_segments(c, "A0", [{"IDVDT": "Hatchback", "IDVS": "Compact", "FuelGroup": "Z"}])
    assert md.restore_workbook_segments(c, "A0") == n
    assert md.reference_params(c, "A0") == antes     # o padrao do Excel volta (60/60)
    c.close()


def test_veiculo_mais_proximo_da_referencia(conn):
    prox = md.closest_vehicles(conn, "A0", limite=3)
    assert prox[0]["Model"] == "ARGO"                # o representativo escolhido no Excel
    assert prox == sorted(prox, key=lambda r: r["Distance"])
    assert md.closest_vehicles(conn, "A5", limite=1)[0]["Model"] == "STRADA"


def test_area_frontal_vem_do_parametro_p59(conn):
    fator = conn.execute("SELECT ValueEC FROM P59_EquationConstant WHERE "
                         "IDEC='FRONTAL_AREA_FACTOR'").fetchone()[0]
    assert fator == 0.85
