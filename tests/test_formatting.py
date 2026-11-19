"""Formato de exibicao (T47): so a exibicao muda, o resultado nunca e arredondado."""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from core import formatting as fm


def test_padrao_um_decimal_em_massa_e_ghg():
    assert fm.fmt(12345.678, "mass") == "12,345.7"
    assert fm.fmt(12345.678, "ghg", with_unit=True) == "12,345.7 kg CO₂e"
    assert fm.fmt(None, "mass") == "—" and fm.fmt(float("nan"), "ghg") == "—"


def test_unidades_toneladas_e_percentual():
    f = fm.from_dict({"mass_unit": "t", "ghg_unit": "t"})
    assert fm.fmt(12345.678, "mass", f, with_unit=True) == "12.3 t"
    assert fm.fmt(0.1234, "share", f) == "12.34"
    g = fm.from_dict({"share_as": "fraction"})
    assert fm.fmt(0.1234, "share", g) == "0.12"
    assert fm.scale(1500.0, "ghg", f) == 1.5 and fm.scale(0.25, "share", fm.DEFAULT) == 25.0


def test_separadores_brasileiros():
    f = fm.from_dict({"decimal_sep": ",", "thousands_sep": ".", "csv_sep": ";"})
    assert fm.fmt(1234567.891, "mass", f) == "1.234.567,9"


def test_perfil_auditoria_usa_precisao_total_e_artigo_arredonda():
    a = fm.profile("audit")
    assert fm.fmt(1234.5678901234, "mass", a) == "1234.5678901234"
    p = fm.profile("article")
    assert p.decimals["factor"] == 3 and fm.fmt(0.00012, "factor", p) == "1.200e-04"


def test_notacao_cientifica_so_abaixo_do_limite():
    f = fm.from_dict({"sci_below": 0.001})
    assert fm.fmt(0.0001234, "factor", f) == "1.2340e-04"
    assert fm.fmt(0.5, "factor", f) == "0.5000" and fm.fmt(0, "factor", f) == "0.0000"


def test_validacao_recusa_combinacoes_invalidas():
    for d in ({"decimal_sep": ",", "thousands_sep": ","}, {"decimal_sep": ","},
              {"mass_unit": "g"}, {"decimals": {"mass": 13}}, {"sci_below": -1},
              {"share_as": "pp"}):
        with pytest.raises(ValueError):
            fm.from_dict(d)


def test_frame_escala_e_arredonda_sem_tocar_no_original():
    df = pd.DataFrame({"kg": [1234.5678, 2000.0], "s": [0.5, 0.25], "x": [1, 2]})
    f = fm.from_dict({"mass_unit": "t"})
    out = fm.frame(df, {"kg": "mass", "s": "share"}, f, rename=True)
    assert list(out.columns) == ["kg (t)", "s (%)", "x"]
    assert out["kg (t)"].tolist() == [1.2, 2.0] and out["s (%)"].tolist() == [50.0, 25.0]
    assert df["kg"].tolist() == [1234.5678, 2000.0]            # o resultado nao e arredondado


def test_formato_de_celula_do_xlsx():
    assert fm.excel_number_format("mass") == "#,##0.0"
    assert fm.excel_number_format("share") == "0.00%"
    assert fm.excel_number_format("ghg", fm.from_dict({"ghg_unit": "t"})) == "#,##0.0,"
    assert fm.excel_number_format("distance") == "#,##0"


def test_csv_nao_arredonda_salvo_pedido():
    df = pd.DataFrame({"kg": [1234.5678]})
    f = fm.from_dict({"csv_sep": ";", "decimal_sep": ",", "thousands_sep": "."})
    assert fm.csv_text(df, {"kg": "mass"}, f) == "kg\n1234,5678\n"
    assert "1234,5678" in fm.csv_text(df, {"kg": "mass"}, f)
    g = fm.from_dict({"csv_sep": ";", "decimal_sep": ",", "thousands_sep": ".",
                      "csv_rounded": True})
    assert "1234,6" in fm.csv_text(df, {"kg": "mass"}, g)


def test_gravar_e_ler_no_projeto():
    conn = sqlite3.connect(":memory:")
    assert fm.load(conn) == (fm.DEFAULT, False)               # sem D22
    conn.execute("CREATE TABLE D22_FormatSetting (SettingKey TEXT PRIMARY KEY, "
                 "SettingValue TEXT NOT NULL)")
    assert fm.load(conn) == (fm.DEFAULT, False)               # sem linha
    f = fm.from_dict({"profile": "custom", "mass_unit": "t", "decimals": {"mass": 3}})
    fm.save(conn, f)
    lido, gravado = fm.load(conn)
    assert gravado and lido == f and lido.decimals["mass"] == 3 and lido.decimals["ghg"] == 1
    fm.save(conn, fm.profile("audit"))                         # sobrescreve
    assert fm.load(conn)[0].decimals["mass"] is None
    assert "precisao total" in fm.describe(fm.profile("audit"))


def _tabelas():
    return {"R00": pd.DataFrame({"Key": ["ValidationStatus"], "Value": ["APROVADO"]}),
            "R10": pd.DataFrame({"IDV": [1], "DsV": ["x"], "IDVPT": ["ICEV"],
                                 "MassIDV": [1234.5678], "GHGCradleToGate": [8765.4321],
                                 "GHGperKg": [0.123456]})}


def test_exportacoes_seguem_o_formato_sem_alterar_os_valores(tmp_path):
    import zipfile

    import openpyxl

    from core import export
    f = fm.from_dict({"profile": "custom", "mass_unit": "t", "csv_sep": ";", "decimal_sep": ",",
                      "thousands_sep": "."})
    R = _tabelas()
    xl = openpyxl.load_workbook(export.to_xlsx(R, str(tmp_path / "a.xlsx"), f))
    ws = xl["R10"]
    cab = [c.value for c in ws[1]]
    i = cab.index("MassIDV") + 1
    assert ws.cell(row=2, column=i).value == pytest.approx(1234.5678)     # valor intacto
    assert ws.cell(row=2, column=i).number_format == "#,##0.0,"           # t via formato
    assert ws.cell(row=2, column=cab.index("GHGperKg") + 1).number_format == "#,##0.000"
    z = zipfile.ZipFile(export.to_csv_zip(R, str(tmp_path / "a.zip"), fmt=f))
    texto = z.read("R10.csv").decode("utf-8-sig", errors="ignore")
    assert ";" in texto and "1234,5678" in texto                           # CSV nao arredonda
    g = fm.from_dict({"csv_rounded": True})
    z = zipfile.ZipFile(export.to_csv_zip(R, str(tmp_path / "b.zip"), fmt=g))
    assert "1234.6" in z.read("R10.csv").decode("utf-8-sig", errors="ignore")
    # sem formato: o comportamento anterior, sem notas novas
    sem = zipfile.ZipFile(export.to_csv_zip(R, str(tmp_path / "c.zip")))
    assert "1234,5678" in sem.read("R10.csv").decode("utf-8-sig", errors="ignore")


def test_html_com_formato_traz_unidade_no_cabecalho_e_descricao():
    from core import export
    f = fm.from_dict({"profile": "custom", "mass_unit": "t"})
    html = export._html_table(_tabelas()["R10"], fmt=f)
    assert "MassIDV [t]" in html and "1.2" in html and "1234.5678" not in html
    assert "MassIDV" in export._html_table(_tabelas()["R10"]) and "[t]" not in \
        export._html_table(_tabelas()["R10"])
