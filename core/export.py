"""Writing the R tables out: XLSX, CSV, HTML and PDF.

Documento 4, capitulo 6. Two rules govern everything here:

* **exporting always recalculates.** This module never sees a cache -- it
  receives tables that were just built, so a file that leaves the calculator
  corresponds by construction to the current state of the data;
* **full precision.** Numbers are written as `float64` gives them. Rounding is
  the reader's decision, and rounding on the way out would make the 1e-6
  validation of Documento 1 impossible to reproduce from the file.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import os
import zipfile

import pandas as pd

from .report import TITLES

#: Documento 4, secao 6.2: ';' and ',' for a Brazilian spreadsheet, '.' and ','
#: for anything that will be read by R, Python or Stata.
CSV_DIALECTS = {
    "br": {"sep": ";", "decimal": ",", "encoding": "utf-8-sig"},
    "iso": {"sep": ",", "decimal": ".", "encoding": "utf-8"},
}


def filename(prefix: str, extension: str, folder: str,
             today: dt.date | None = None) -> str:
    """`<prefix>_<AAAAMMDD><letra>.<ext>`, the letter advancing (diretriz D6)."""
    today = today or dt.date.today()
    stamp = today.strftime("%Y%m%d")
    ultimo = None
    for letra in "abcdefghijklmnopqrstuvwxyz":
        caminho = os.path.join(folder, f"{prefix}_{stamp}{letra}.{extension}")
        if not os.path.exists(caminho):
            return caminho
        ultimo = caminho
    return ultimo


def index_table(R: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """The first sheet: what is in the file, and how much of it.

    An empty table is not a defect -- a scenario that reads assembly from the
    factor table has no energy rows -- so the count is shown rather than the
    sheet hidden.
    """
    linhas = [{"Tabela": k, "Conteudo": TITLES.get(k, ""),
               "Linhas": len(df), "Colunas": len(df.columns)}
              for k, df in sorted(R.items())]
    return pd.DataFrame(linhas)


def to_xlsx(R: dict[str, pd.DataFrame], path: str) -> str:
    """One sheet per table, headers frozen, columns sized to their content."""
    from openpyxl.styles import Alignment, Font, PatternFill

    fill = PatternFill("solid", fgColor="1F3864")
    font = Font(color="FFFFFF", bold=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        index_table(R).to_excel(writer, sheet_name="INDICE", index=False)
        for nome, df in sorted(R.items()):
            df.to_excel(writer, sheet_name=nome, index=False)
        for nome in writer.book.sheetnames:
            ws = writer.book[nome]
            for c in ws[1]:
                c.fill = fill
                c.font = font
                c.alignment = Alignment(vertical="center")
            ws.freeze_panes = "A2"
            for i, col in enumerate(ws.iter_cols(min_row=1, max_row=1), 1):
                largura = max(len(str(col[0].value or "")) + 2, 10)
                ws.column_dimensions[
                    ws.cell(row=1, column=i).column_letter].width = min(largura, 42)
    return path


def to_csv_zip(R: dict[str, pd.DataFrame], path: str, *, dialect: str = "br") -> str:
    """One `.csv` per table inside one `.zip`, so nothing arrives half-copied."""
    if dialect not in CSV_DIALECTS:
        raise ValueError(f"dialeto desconhecido: {dialect}")
    cfg = CSV_DIALECTS[dialect]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        buf = io.StringIO()
        index_table(R).to_csv(buf, index=False, sep=cfg["sep"],
                              decimal=cfg["decimal"], quoting=csv.QUOTE_MINIMAL)
        z.writestr("INDICE.csv", buf.getvalue().encode(cfg["encoding"]))
        for nome, df in sorted(R.items()):
            buf = io.StringIO()
            df.to_csv(buf, index=False, sep=cfg["sep"], decimal=cfg["decimal"],
                      quoting=csv.QUOTE_MINIMAL)
            z.writestr(f"{nome}.csv", buf.getvalue().encode(cfg["encoding"]))
    return path


# --------------------------------------------------------------------------
# HTML e PDF
# --------------------------------------------------------------------------
# Documento 4, secao 6.2.1: os dois formatos compartilham conteudo e gerador,
# o que impede que divirjam. O XLSX e uma colecao de tabelas; o HTML e o PDF
# sao um documento que se le, e por isso cada secao traz a equacao aplicada.

#: Paleta categorica validada (data-viz de referencia), nas duas superficies.
#: A ordem dos slots e o mecanismo de seguranca para daltonismo, nao enfeite.
PALETA_CLARA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                "#e87ba4", "#008300", "#4a3aa7"]
PALETA_ESCURA = ["#3987e5", "#d95926", "#199e70", "#c98500",
                 "#d55181", "#008300", "#9085e9"]

#: Tabelas grandes demais para ficarem abertas por padrao na tela.
LIMITE_ABERTO = 60

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ titulo }}</title>
<style>
:root {
  color-scheme: light;
  --plano: #f9f9f7; --superficie: #fcfcfb;
  --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #898781;
  --grade: #e1e0d9; --eixo: #c3c2b7; --borda: rgba(11,11,11,0.10);
  --bom: #006300; --critico: #d03b3b;
  --chart-other: #898781;
{% for c in paleta_clara %}  --serie-{{ loop.index }}: {{ c }};
{% endfor %}}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --plano: #0d0d0d; --superficie: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --ink-3: #898781;
    --grade: #2c2c2a; --eixo: #383835; --borda: rgba(255,255,255,0.10);
    --bom: #0ca30c; --critico: #d03b3b;
{% for c in paleta_escura %}    --serie-{{ loop.index }}: {{ c }};
{% endfor %}  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--plano); color: var(--ink);
       font: 15px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 32px 16px 80px; }
h1 { font-size: 26px; line-height: 1.25; margin: 0 0 4px; }
h2 { font-size: 19px; margin: 40px 0 8px; padding-top: 16px;
     border-top: 1px solid var(--borda); }
h3 { font-size: 15px; margin: 24px 0 6px; color: var(--ink-2); }
p { margin: 8px 0; }
.sub { color: var(--ink-2); margin: 0 0 20px; }
.selo { display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: 13px; font-weight: 600; }
.selo.ok { color: var(--bom); border: 1px solid var(--bom); }
.selo.erro { color: var(--critico); border: 1px solid var(--critico); }
.equacao { background: var(--superficie); border: 1px solid var(--borda);
           border-left: 3px solid var(--serie-1); border-radius: 6px;
           padding: 10px 14px; margin: 12px 0; color: var(--ink-2);
           font-size: 14px; }
.equacao code { color: var(--ink); font-size: 14px; }
figure { margin: 18px 0 8px; background: var(--superficie);
         border: 1px solid var(--borda); border-radius: 8px; padding: 14px; }
figcaption { color: var(--ink-2); font-size: 13px; margin-top: 8px; }
svg.grafico { width: 100%; height: auto; display: block; }
svg .grid { stroke: var(--grade); stroke-width: 1; }
svg .eixo { stroke: var(--eixo); stroke-width: 1; }
svg .barra { fill: var(--serie-1); }
svg .rotulo, svg .legenda { fill: var(--ink-2); font-size: 12px;
                            font-family: inherit; }
svg .valor, svg .tick, svg .unidade { fill: var(--ink-2); font-size: 11px;
       font-family: inherit; font-variant-numeric: tabular-nums; }
svg .valor { fill: var(--ink); }
svg .mark:hover path { opacity: 0.82; }
table { border-collapse: collapse; width: 100%; font-size: 13px;
        font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--borda);
         white-space: nowrap; }
th { color: var(--ink-2); font-weight: 600; position: sticky; top: 0;
     background: var(--plano); }
td.num, th.num { text-align: right; }
.rolagem { overflow-x: auto; background: var(--superficie);
           border: 1px solid var(--borda); border-radius: 8px; padding: 4px 8px; }
details { margin: 10px 0; }
summary { cursor: pointer; color: var(--ink-2); font-size: 14px; padding: 4px 0; }
.nota { color: var(--ink-3); font-size: 13px; }
footer { margin-top: 48px; color: var(--ink-3); font-size: 13px;
         border-top: 1px solid var(--borda); padding-top: 12px; }
@media print {
  body { background: #fff; }
  main { max-width: none; padding: 0; }
  h2 { break-before: auto; break-after: avoid; }
  figure, table { break-inside: auto; }
  tr { break-inside: avoid; }
  details > *:not(summary) { display: revert !important; }
  details { display: block; }
  summary { list-style: none; font-weight: 600; color: #000; }
  .rolagem { overflow: visible; border: none; padding: 0; }
  table { font-size: 9px; }
  th, td { white-space: normal; padding: 2px 4px; }
  th { position: static; }
  @page { size: A4; margin: 18mm 14mm; @bottom-center { content: counter(page); } }
}
</style>
</head>
<body>
<main>
<h1>{{ titulo }}</h1>
<p class="sub">{{ subtitulo }}</p>
<p><span class="selo {{ 'ok' if aprovado else 'erro' }}">{{ selo }}</span></p>

<h2>1. Identificação da execução</h2>
{{ tabela_meta }}

<h2>2. Resultado do berço ao portão</h2>
<div class="equacao">
  <code>GHG<sub>berço→portão</sub> = Σ<sub>grupos</sub> GHG<sub>grupo</sub>
  + GHG<sub>montagem</sub></code><br>
  A montagem entra quando a fronteira do cenário é <code>MAT_ASM</code>;
  em <code>MAT</code> ela é calculada e informada, mas não somada.
</div>
<figure>{{ grafico_total }}
<figcaption>{{ legenda_total }}</figcaption></figure>
{{ tabela_total }}

<h2>3. Decomposição por grupo GREET</h2>
<div class="equacao">
  <code>GHG<sub>grupo</sub> = Σ<sub>materiais</sub> Massa<sub>material</sub>
  × EF<sub>material</sub></code><br>
  com <code>Massa<sub>material</sub> = Massa<sub>grupo</sub> ×
  MshareGG</code>, e a bateria de tração pelo caminho declarado em
  <code>P19.GHGMethod</code>.
</div>
<figure>{{ grafico_grupos }}
<figcaption>{{ legenda_grupos }}</figcaption></figure>
{{ tabela_grupos }}

<h2>4. Materiais que mais pesam</h2>
{{ tabela_materiais }}

<h2>5. Montagem do veículo</h2>
<div class="equacao">
  <code>GHG<sub>montagem</sub></code> — conforme <code>P23.Method</code>:
  <code>from_EF</code> lê o valor da própria tabela de fatores (IDM 99);
  <code>process</code> soma energia × participação de cada combustível;
  <code>fixed</code> usa um valor por veículo.
</div>
{{ tabela_montagem }}

<h2>6. Validação e cobertura</h2>
<p>{{ texto_validacao }}</p>
{{ tabela_validacao }}
<p class="nota">Fator de emissão ausente não é emissão zero: a massa
correspondente continua no total de massa e aparece em
<code>MassNoFactor</code>.</p>

<h2>7. Anexo: tabelas completas</h2>
<p class="nota">Cada tabela repete o cenário a que pertence, e as tabelas
detalhadas trazem os próprios insumos — participação, fator, expoente — para
que a conta possa ser refeita fora do programa.</p>
{{ anexo }}

<footer>{{ rodape }}</footer>
</main>
</body>
</html>
"""


def _html_table(df: pd.DataFrame, *, casas: int = 3, maximo: int | None = None) -> str:
    """A table as HTML, numbers right-aligned and tabular, no masks applied."""
    if not len(df):
        return '<p class="nota">Tabela vazia neste conjunto de cenários.</p>'
    corte = df if maximo is None else df.head(maximo)
    numericas = {c for c in corte.columns
                 if pd.api.types.is_numeric_dtype(corte[c])
                 and c not in ("IDV", "IDEA", "IDVP", "IDSG", "IDMPV", "IDAP")}
    cabecalho = "".join(
        f'<th class="{"num" if c in numericas else ""}">{_esc(c)}</th>'
        for c in corte.columns)
    linhas = []
    for _, r in corte.iterrows():
        celulas = []
        for c in corte.columns:
            v = r[c]
            if c in numericas and pd.notna(v):
                celulas.append(f'<td class="num">{_num(v, casas)}</td>')
            else:
                celulas.append(f"<td>{'' if pd.isna(v) else _esc(v)}</td>")
        linhas.append("<tr>" + "".join(celulas) + "</tr>")
    resto = ""
    if maximo is not None and len(df) > maximo:
        resto = (f'<p class="nota">Mostrando {maximo} de {len(df)} linhas. '
                 f'O conjunto completo está no XLSX e no CSV.</p>')
    return (f'<div class="rolagem"><table><thead><tr>{cabecalho}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>{resto}')


def _esc(v) -> str:
    import html as _h
    return _h.escape(str(v), quote=True)


def _num(v, casas: int) -> str:
    if isinstance(v, (int,)) or (isinstance(v, float) and float(v).is_integer()
                                 and abs(v) < 1e15):
        s = f"{v:,.0f}"
    else:
        s = f"{v:,.{casas}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


#: Nomes curtos dos grupos GREET para a legenda. O nome completo fica no
#: rotulo de passagem do segmento e na tabela R07, logo abaixo do grafico.
NOMES_CURTOS = {
    "A": "Carroceria", "B": "Chassi", "C": "Motor elétrico",
    "D": "Trem de força", "E": "Transmissão", "F": "Gerador",
    "G": "Controlador", "H": "Célula a combustível", "J": "Carregador",
    "K": "Fluidos", "Iaux": "Bateria auxiliar", "Iprinc": "Bateria de tração",
}


def _rotulo_grupo(idgg, descricao) -> str:
    curto = NOMES_CURTOS.get(str(idgg))
    if curto is None:
        curto = str(descricao)[:18]
    return f"{idgg} · {curto}"


def to_html(R: dict[str, pd.DataFrame], path: str, *, titulo: str | None = None) -> str:
    """The narrated report: the same content the PDF will carry."""
    from jinja2 import Template

    from . import charts

    meta = dict(zip(R["R00"]["Key"], R["R00"]["Value"]))
    aprovado = str(meta.get("ValidationStatus", "")) == "APROVADO"
    r10 = R["R10"]
    r07 = R["R07"]

    rotulo = {int(r.IDV): f"{r.DsV} ({r.IDVPT})" for r in r10.itertuples()}
    total = [(rotulo[int(r.IDV)], float(r.GHGCradleToGate)) for r in r10.itertuples()]
    grafico_total = charts.bar_chart(total, unidade="kg CO₂e por veículo",
                                     titulo="Emissões do berço ao portão")

    por_grupo: dict[str, dict] = {}
    nomes = dict(zip(r07["IDGG"], r07["DsGG"]))
    for r in r07.itertuples():
        chave = rotulo.get(int(r.IDV), str(r.IDV))
        nome = _rotulo_grupo(r.IDGG, nomes.get(r.IDGG, ""))
        por_grupo.setdefault(chave, {})[nome] = (
            por_grupo.setdefault(chave, {}).get(nome, 0.0) + float(r.GHGIDGG))
    linhas_grupo = [(k, v) for k, v in por_grupo.items()]
    linhas_grupo, series = charts.top_series(linhas_grupo)
    grafico_grupos = charts.stacked_bar_chart(
        linhas_grupo, series, unidade="kg CO₂e",
        titulo="Emissões por grupo GREET")

    materiais = (R["R08"].groupby(["IDM", "DsM"], as_index=False, dropna=False)
                 .agg(MassIDM=("MassIDM", "sum"), GHGIDM=("GHGIDM", "sum"))
                 .sort_values("GHGIDM", ascending=False).head(15))

    erros = int(meta.get("ValidationErrors", 0) or 0)
    avisos = int(meta.get("ValidationWarnings", 0) or 0)
    sem_fator = float(r10["MassNoFactor"].max()) if len(r10) else 0.0
    parcela = float(r10["ShareNoFactor"].max()) if len(r10) else 0.0
    texto_validacao = (
        f"{erros} erro(s) e {avisos} aviso(s) na execução. "
        f"No veículo em pior situação, {_num(sem_fator, 3)} kg de massa "
        f"({_num(parcela * 100, 2)}% do total) não têm fator de emissão "
        f"publicado na versão escolhida.")

    anexo = []
    from .report import TITLES
    for nome, df in sorted(R.items()):
        aberto = " open" if len(df) <= LIMITE_ABERTO else ""
        anexo.append(
            f'<details{aberto}><summary>{_esc(nome)} — '
            f'{_esc(TITLES.get(nome, ""))} ({len(df)} linhas)</summary>'
            f'{_html_table(df, maximo=400)}</details>')

    html_final = Template(TEMPLATE).render(
        titulo=titulo or "Pegada de carbono do berço ao portão",
        subtitulo=(f"Gerado em {meta.get('GeneratedAt', '')} · "
                   f"programa {meta.get('ProgramVersion', '')} · "
                   f"base {str(meta.get('ParamBaseHash', ''))[:16]} · "
                   f"{meta.get('Metric', '')}"),
        selo=("Validação aprovada" if aprovado else "Validação reprovada"),
        aprovado=aprovado,
        paleta_clara=PALETA_CLARA, paleta_escura=PALETA_ESCURA,
        tabela_meta=_html_table(R["R00"]),
        grafico_total=grafico_total,
        legenda_total=("Total do berço ao portão por veículo, na fronteira de cada "
                       "cenário. Os valores completos estão na tabela abaixo."),
        tabela_total=_html_table(r10),
        grafico_grupos=grafico_grupos,
        legenda_grupos=("Composição das emissões por grupo GREET, **sem a "
                        "montagem** — por isso os totais aqui são menores que os "
                        "da seção 2. Os grupos além dos sete maiores aparecem "
                        "somados em “Outros”; a tabela R07, no anexo, traz todos "
                        "separadamente.").replace("**", ""),
        tabela_grupos=_html_table(r07, maximo=LIMITE_ABERTO),
        tabela_materiais=_html_table(materiais),
        tabela_montagem=_html_table(R["R09"]),
        texto_validacao=texto_validacao,
        tabela_validacao=_html_table(R["R11"]),
        anexo="".join(anexo),
        rodape=("Calculadora da Pegada de Carbono de Veículos Leves — do Berço ao "
                "Portão · NIPE/UNICAMP · Fatores derivados do GREET (UChicago "
                "Argonne, LLC), uso não comercial · kg CO₂e, GWP-100, IPCC AR6."),
    )
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html_final)
    return path


def to_pdf(html_path: str, path: str) -> str | None:
    """The same HTML, paginated. Absent WeasyPrint, the HTML stands alone.

    Documento 4, secao 6.2.1: the calculation never depends on this. If the
    system libraries are not there, the feature degrades and says so -- the
    browser's own "print to PDF" uses the print stylesheet already in the file.
    """
    try:
        from weasyprint import HTML
    except Exception:
        return None
    HTML(filename=html_path).write_pdf(path)
    return path
