"""The pieces every screen shares.

Three of them are not decoration. The **version bar** keeps the four versions
and the boundary in sight, because two results are comparable only if the
versions are stated. The **validation panel** is green or it is red, and when it
is red it says which rule broke. **"How was this calculated?"** opens the
equation, its inputs and where in Documento 1 it is specified -- the didactic
purpose of the project lives in that expander.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import __version__

from . import state

DOC1 = "docs/01-especificacao-funcional.md"


def page(titulo: str, capitulo: str = "", *, exige_projeto: bool = True):
    """Standard header. Returns the open project, or stops the page."""
    st.set_page_config(page_title=f"{titulo} · i3ET Calculator", layout="wide")
    st.title(titulo)
    if capitulo:
        st.caption(f"Specified in {DOC1}, {capitulo}")
    if not exige_projeto:
        return None
    atual = state.current()
    if atual is None:
        st.info("Open or create a project on the **Home** page first.")
        st.stop()
    version_bar(atual[0], atual[2])
    return atual


def version_bar(base, log) -> None:
    """The four versions in use, the boundary, and whether it all validates."""
    d02 = base["D02"]

    def unicos(coluna, mostrar: int = 2):
        """Os valores em uso. Muitos viram "os dois primeiros +N".

        Um projeto com doze veiculos pode usar seis receitas, e listar as seis
        aqui empurra o resto da barra para fora da linha. A lista inteira esta
        na tela **Scenario** e em `R01`.
        """
        vals = sorted({str(v) for v in d02[coluna]})
        if not vals:
            return "—"
        if len(vals) <= mostrar:
            return ", ".join(vals)
        return ", ".join(vals[:mostrar]) + f" +{len(vals) - mostrar}"

    proprias = set(base["D04"]["IDEFV"]) if len(base.get("D04", [])) else set()
    efv = unicos("IDEFV")
    if proprias & set(d02["IDEFV"]):
        efv += "  ·  user-defined"

    # Uma linha, nao seis caixas: os identificadores sao longos, e uma caixa
    # estreita os corta justamente onde esta a informacao (`PBP_BISD2s` vira
    # `PBP_B…`). A barra existe para ser lida inteira.
    itens = [("Mass params", unicos("IDMPV")),
             ("Material recipe", unicos("IDVMR")),
             ("Emission factors", efv),
             ("Assembly", unicos("IDAPV")),
             ("Boundary", unicos("Boundary")),
             ("Project", state.project_name())]
    st.markdown(" &nbsp;·&nbsp; ".join(
        f"**{rotulo}** `{valor}`" for rotulo, valor in itens))
    st.caption(f"Reference base `{(base.param_hash or '')[:16]}` · "
               f"program {__version__}")
    validation_panel(log, compacto=True)


def validation_panel(log, *, compacto: bool = False) -> None:
    erros, avisos = log.of("ERRO"), log.of("AVISO")
    if erros:
        st.error(f"**Validation failed** — {len(erros)} error(s). "
                 "Nothing may be exported until they are resolved.")
        for e in erros[:8]:
            st.write(f"- `{e.rule}` {e.message}"
                     + (f"  _({e.context})_" if e.context else ""))
    elif avisos and not compacto:
        st.warning(f"Validation passed with {len(avisos)} warning(s).")
    elif not compacto:
        st.success("Validation passed: every invariant holds.")
    if avisos and compacto:
        with st.expander(f"{len(avisos)} warning(s)"):
            for a in avisos[:40]:
                st.write(f"- `{a.rule}` {a.message}")


def how_was_this_calculated(titulo: str, equacao: str, entradas: dict,
                            referencia: str) -> None:
    """The expander that turns a number back into an equation."""
    with st.expander(f"How was this calculated? — {titulo}"):
        st.code(equacao, language="text")
        if entradas:
            st.dataframe(pd.DataFrame(
                [{"Input": k, "Value": v} for k, v in entradas.items()]),
                hide_index=True, use_container_width=True)
        st.caption(f"{DOC1} — {referencia}")


#: As mesmas cores da paleta validada que o relatorio exportado usa, para que
#: a tela e o arquivo nao se contradigam. Sao declaradas uma vez por pagina.
ESTILO_GRAFICO = """
<style>
.viz-i3et { --superficie: transparent; --ink: inherit; }
.viz-i3et svg.grafico { width: 100%; height: auto; display: block;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.viz-i3et svg .grid { stroke: rgba(128,128,128,0.25); stroke-width: 1; }
.viz-i3et svg .eixo { stroke: rgba(128,128,128,0.55); stroke-width: 1; }
.viz-i3et svg .ligacao { stroke: rgba(128,128,128,0.55); stroke-width: 1;
  stroke-dasharray: 3 3; }
.viz-i3et svg .barra { fill: #2a78d6; }
.viz-i3et svg .total { fill: #52514e; }
.viz-i3et svg .rotulo, .viz-i3et svg .legenda { fill: currentColor;
  opacity: 0.75; font-size: 12px; }
.viz-i3et svg .valor, .viz-i3et svg .tick, .viz-i3et svg .unidade {
  fill: currentColor; opacity: 0.8; font-size: 11px;
  font-variant-numeric: tabular-nums; }
.viz-i3et svg .mark:hover path { opacity: 0.82; }
</style>
"""


def chart(svg: str) -> None:
    """Desenha um SVG de `core.charts` na pagina.

    O mesmo gerador que escreve o relatorio exportado desenha a tela: um
    grafico so, em dois lugares, sem chance de divergirem.
    """
    if not svg:
        st.caption("Nothing to plot for this selection.")
        return
    st.markdown(ESTILO_GRAFICO + f'<div class="viz-i3et">{svg}</div>',
                unsafe_allow_html=True)


def number(valor, casas: int = 3) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    return f"{valor:,.{casas}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def table(df: pd.DataFrame, *, altura: int | None = None) -> None:
    st.dataframe(df, hide_index=True, use_container_width=True,
                 height=altura if altura else None)


def coverage_note(totais: dict) -> None:
    """Missing factor is absence of data, and the screen says so every time."""
    parcela = float(totais.get("ShareNoFactor") or 0.0)
    massa = float(totais.get("MassNoFactor") or 0.0)
    if massa <= 0:
        st.caption("Every kilogram of this vehicle has a published emission "
                   "factor in the selected version.")
        return
    st.caption(f"**{number(massa)} kg** ({number(parcela * 100, 2)}%) of this "
               "vehicle's mass has no published factor in the selected version. "
               "That mass is counted in the mass total and contributes nothing "
               "to the emissions — absence of data, not zero emissions.")
