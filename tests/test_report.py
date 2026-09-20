"""The R tables and the files they become.

Documento 4, capitulos 5 e 6. What is checked here is not the arithmetic --
that is the job of the other modules -- but the three promises the export
makes: every row says which scenario it belongs to, the parameters that
travel with the results are the ones that produced them, and what comes out
of the file is what went into it.
"""

from __future__ import annotations

import os
import zipfile

import pandas as pd
import pytest

from core import calc, export, report, validate
from core.log import Log

RESULT_TABLES = ["R01", "R02", "R03", "R04", "R05", "R07", "R08", "R09", "R10"]


@pytest.fixture(scope="module")
def R(base):
    log = Log()
    validate.check_base(base, log)
    resultados = calc.calculate(base, log=log)
    for (idv, idea), r in resultados.items():
        validate.check_result(r, log, context=f"IDV {idv} / IDEA {idea}")
    return report.build(base, resultados, log=log)


def test_every_documented_table_exists(R):
    esperadas = set(report.TITLES)
    assert esperadas <= set(R), f"faltam: {sorted(esperadas - set(R))}"


def test_every_table_has_a_title(R):
    sem_titulo = [k for k in R if not report.TITLES.get(k)]
    assert not sem_titulo, sem_titulo


def test_every_result_row_says_which_scenario_it_belongs_to(R):
    """Documento 4, secao 5.1, item 2: a sheet pulled out still says what it is."""
    for nome in RESULT_TABLES:
        df = R[nome]
        if not len(df):
            continue
        faltando = [c for c in report.SCENARIO_KEYS if c not in df.columns]
        assert not faltando, f"{nome} sem {faltando}"
        assert df[report.SCENARIO_KEYS].notna().all().all(), nome
        assert "IDV" in df.columns and "IDEA" in df.columns, nome


def test_detailed_tables_carry_their_own_inputs(R):
    """Item 3: whoever opens the file can redo the arithmetic."""
    for coluna in ("Beta", "GCR", "MR", "GC", "fLM"):
        assert coluna in R["R03"].columns, coluna
    for coluna in ("MshareGG", "EF", "MassIDMpGG", "GHGIDMpGG"):
        assert coluna in R["R05"].columns, coluna


def test_the_total_table_matches_the_calculation(base, R):
    atual = calc.calculate(base)
    r10 = R["R10"].set_index(["IDV", "IDEA"])
    assert len(r10) == len(atual)
    for (idv, idea), r in atual.items():
        linha = r10.loc[(idv, idea)]
        assert linha["MassIDV"] == pytest.approx(r["totals"]["MassIDV"], rel=1e-12)
        assert linha["GHGCradleToGate"] == pytest.approx(
            r["totals"]["GHGCradleToGate"], rel=1e-12)


def test_the_group_table_adds_up_to_the_total(R):
    soma = R["R07"].groupby(["IDV", "IDEA"])[["MassIDGG", "GHGIDGG"]].sum()
    r10 = R["R10"].set_index(["IDV", "IDEA"])
    for chave, linha in r10.iterrows():
        assert soma.loc[chave, "MassIDGG"] == pytest.approx(linha["MassIDV"], rel=1e-9)
        assert soma.loc[chave, "GHGIDGG"] == pytest.approx(
            linha["GHGMaterials"], rel=1e-9)


def test_the_material_table_adds_up_to_the_total(R):
    soma = R["R08"].groupby(["IDV", "IDEA"])[["MassIDM", "GHGIDM"]].sum()
    r10 = R["R10"].set_index(["IDV", "IDEA"])
    for chave, linha in r10.iterrows():
        assert soma.loc[chave, "MassIDM"] == pytest.approx(linha["MassIDV"], rel=1e-9)


def test_the_parameter_snapshot_carries_only_what_was_used(base, R):
    """The exported set is self-contained, and no larger than it needs to be."""
    usadas = set(R["R01"]["IDVMR"])
    assert set(R["R32"]["IDVMR"]) == usadas
    assert set(R["R33"]["IDVMR"]) == usadas
    assert set(R["R28"]["IDEFV"]) == set(R["R01"]["IDEFV"])
    assert len(R["R33"]) < len(base["P16"]), "P16 inteira foi exportada"


def test_the_snapshot_covers_every_material_the_results_mention(R):
    citados = set(R["R05"]["IDM"].dropna()) | set(R["R08"]["IDM"].dropna())
    assert citados <= set(R["R26"]["IDM"]), "material sem descricao no anexo"


def test_the_emission_factor_versions_say_who_wrote_them(R):
    assert "IsUserDefined" in R["R27"].columns
    assert R["R27"]["IsUserDefined"].isin([0, 1]).all()


def test_metadata_answers_whether_the_file_may_be_trusted(R, base):
    meta = dict(zip(R["R00"]["Key"], R["R00"]["Value"]))
    assert meta["ParamBaseHash"] == base.param_hash
    assert meta["ValidationStatus"] in ("APROVADO", "REPROVADO")
    assert int(meta["Scenarios"]) == len(R["R10"])
    assert "AR6" in meta["Metric"]


def test_an_empty_table_still_has_its_columns(R):
    """A sheet with no header is a sheet nobody can read."""
    for nome, df in R.items():
        assert len(df.columns) > 0, nome


# --- os arquivos ----------------------------------------------------------

def test_xlsx_round_trips_the_totals(R, tmp_path):
    caminho = export.to_xlsx(R, str(tmp_path / "r.xlsx"))
    lido = pd.read_excel(caminho, sheet_name="R10")
    assert len(lido) == len(R["R10"])
    assert lido["GHGCradleToGate"].sum() == pytest.approx(
        R["R10"]["GHGCradleToGate"].sum(), rel=1e-12)
    indice = pd.read_excel(caminho, sheet_name="INDICE")
    assert len(indice) == len(R)


def test_csv_zip_has_one_file_per_table(R, tmp_path):
    caminho = export.to_csv_zip(R, str(tmp_path / "r.zip"))
    with zipfile.ZipFile(caminho) as z:
        nomes = set(z.namelist())
        assert nomes == {f"{k}.csv" for k in R} | {"INDICE.csv"}
        bruto = z.read("R10.csv").decode("utf-8-sig")
    assert bruto.startswith("IDV;IDEA"), "dialeto brasileiro esperado"
    assert "," in bruto.splitlines()[1], "decimal brasileiro esperado"


def test_csv_iso_dialect_is_readable_by_pandas(R, tmp_path):
    caminho = export.to_csv_zip(R, str(tmp_path / "iso.zip"), dialect="iso")
    with zipfile.ZipFile(caminho) as z:
        with z.open("R10.csv") as fh:
            lido = pd.read_csv(fh)
    assert lido["GHGCradleToGate"].sum() == pytest.approx(
        R["R10"]["GHGCradleToGate"].sum(), rel=1e-12)


#: O que faria o arquivo depender da rede para se desenhar. Uma URL no meio de
#: um texto -- a nota de direitos autorais do GREET, por exemplo -- nao e
#: dependencia: o navegador nao vai buscar nada por causa dela.
DEPENDENCIAS_EXTERNAS = ("<script", "<img", "src=", "@import", "url(http",
                         'href="http', "<link")


@pytest.fixture(scope="module")
def html(R, tmp_path_factory):
    caminho = export.to_html(R, str(tmp_path_factory.mktemp("html") / "r.html"))
    return open(caminho, encoding="utf-8").read()


def test_html_is_self_contained(html):
    """Tem de abrir de um pen drive daqui a dez anos, sem rede."""
    achadas = [p for p in DEPENDENCIAS_EXTERNAS if p in html]
    assert not achadas, f"dependencias externas: {achadas}"
    assert "<svg" in html and "viewBox" in html


def test_html_brings_both_modes_and_the_print_sheet(html):
    assert "prefers-color-scheme: dark" in html
    assert "@media print" in html


def test_html_shows_the_result_and_the_equations(R, html):
    assert "Validação aprovada" in html
    assert "MshareGG" in html, "a equacao dos materiais sumiu"
    faltando = [v for v in R["R10"]["DsV"] if str(v) not in html]
    assert not faltando, f"veiculos ausentes do relatorio: {faltando}"


def test_the_filename_advances_a_letter_per_version(tmp_path):
    a = export.filename("Resultados", "xlsx", str(tmp_path))
    assert a.endswith("a.xlsx")
    open(a, "w").close()
    b = export.filename("Resultados", "xlsx", str(tmp_path))
    assert b.endswith("b.xlsx") and b != a


def test_an_unknown_csv_dialect_is_refused(R, tmp_path):
    with pytest.raises(ValueError):
        export.to_csv_zip(R, str(tmp_path / "x.zip"), dialect="klingon")


def test_the_pdf_degrades_without_weasyprint(R, tmp_path, monkeypatch):
    """Documento 4: the absence of the library degrades the feature, not the run."""
    html = export.to_html(R, str(tmp_path / "r.html"))
    monkeypatch.setitem(__import__("sys").modules, "weasyprint", None)
    resultado = export.to_pdf(html, str(tmp_path / "r.pdf"))
    assert resultado is None or os.path.exists(resultado)


# --- os graficos ----------------------------------------------------------

def test_a_ninth_category_folds_instead_of_getting_a_ninth_colour():
    """A paleta tem oito posicoes; a nona categoria nao ganha um tom novo."""
    from core import charts
    linhas = [("v", {f"g{i}": float(10 - i) for i in range(10)})]
    novas, series = charts.top_series(linhas, limite=7)
    assert len(series) == 8 and series[-1] == "Outros"
    assert novas[0][1]["Outros"] == pytest.approx(sum(range(1, 4)))
    assert sum(novas[0][1].values()) == pytest.approx(sum(linhas[0][1].values()))


def test_the_biggest_categories_are_the_ones_kept():
    from core import charts
    linhas = [("a", {"x": 1.0, "y": 100.0}), ("b", {"x": 2.0, "z": 50.0})]
    _, series = charts.top_series(linhas, limite=1)
    assert series[0] == "y"


def test_a_chart_with_no_rows_draws_nothing():
    from core import charts
    assert charts.bar_chart([], unidade="kg") == ""
    assert charts.stacked_bar_chart([], [], unidade="kg") == ""


def test_the_bars_are_anchored_to_the_axis_and_rounded_at_the_value():
    from core import charts
    svg = charts.bar_chart([("um", 10.0), ("dois", 5.0)], unidade="kg")
    assert svg.count('class="mark"') == 2
    assert "A4.00,4.00" in svg, "extremidade arredondada ausente"
    assert 'viewBox="0 0 760' in svg


def test_every_segment_says_its_own_value_on_hover():
    from core import charts
    svg = charts.stacked_bar_chart(
        [("v", {"a": 2.0, "b": 3.0})], ["a", "b"], unidade="kg", casas=1,
        titulo="Composicao")
    assert svg.count("<title>") == 3          # um por segmento, um do grafico
    assert "v · a: 2,0 kg" in svg
    assert "var(--serie-1)" in svg and "var(--serie-2)" in svg


def test_numbers_are_written_the_brazilian_way():
    from core import charts
    svg = charts.bar_chart([("x", 1234567.0)], unidade="kg")
    assert "1.234.567" in svg
