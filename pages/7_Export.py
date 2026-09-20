"""Screen 7 — every table, in the format you need.

Documento 4, secao 6.1. One button, and a fixed sequence behind it: recalculate
from D, run the invariants, stop if any error, build R00..R44, generate the
formats. Exporting always recalculates -- a file that leaves the calculator
corresponds by construction to the current state of the data.
"""

from __future__ import annotations

import datetime as dt
import os
import tempfile

import streamlit as st

from core import export, report
from ui import components, state

atual = components.page("Export", "§6 of Documento 4")
base, resultados, log = atual

st.write("Every exported set is self-contained: the results, and exactly the "
         "parameters that produced them. Whoever receives the file can redo "
         "the arithmetic without this program.")

formatos = st.multiselect(
    "Formats", options=["XLSX", "CSV (zip)", "HTML", "PDF"],
    default=["XLSX", "HTML"],
    help="HTML and PDF share the same generator, so they cannot diverge.")
dialeto = st.radio(
    "CSV convention", options=["br", "iso"], horizontal=True,
    format_func=lambda d: ("Brazilian — ; separator, , decimal"
                           if d == "br" else
                           "ISO — , separator, . decimal (R, Python, Stata)"))

erros = log.of("ERRO")
if erros:
    st.error(f"{len(erros)} validation error(s). Nothing can be exported until "
             "they are resolved.")
    components.validation_panel(log)
    st.stop()

if st.button("Generate and export all tables", type="primary"):
    with st.spinner("Recalculating and building the tables…"):
        R = report.build(base, resultados, log=log)
        pasta = tempfile.mkdtemp(prefix="i3et_saidas_")
        prefixo = f"Resultados_{state.project_name()}"
        gerados = []
        if "XLSX" in formatos:
            gerados.append(export.to_xlsx(
                R, export.filename(prefixo, "xlsx", pasta)))
        if "CSV (zip)" in formatos:
            gerados.append(export.to_csv_zip(
                R, export.filename(prefixo, "zip", pasta), dialect=dialeto))
        html = None
        if "HTML" in formatos or "PDF" in formatos:
            html = export.to_html(R, export.filename(prefixo, "html", pasta))
            if "HTML" in formatos:
                gerados.append(html)
        if "PDF" in formatos and html:
            pdf = export.to_pdf(html, export.filename(prefixo, "pdf", pasta))
            if pdf:
                gerados.append(pdf)
            else:
                st.info("PDF not generated: WeasyPrint is not available in "
                        "this environment. The HTML carries the print "
                        "stylesheet — printing it from the browser produces "
                        "the same document.")
        st.session_state["export_files"] = gerados
        st.session_state["export_summary"] = {
            "tables": len(R), "rows": sum(len(df) for df in R.values()),
            "at": dt.datetime.now().strftime("%H:%M:%S")}

resumo = st.session_state.get("export_summary")
if resumo:
    st.success(f"{resumo['tables']} tables, {resumo['rows']} rows, "
               f"built at {resumo['at']}.")
    for caminho in st.session_state.get("export_files", []):
        if not os.path.exists(caminho):
            continue
        with open(caminho, "rb") as fh:
            st.download_button(f"Download {os.path.basename(caminho)}",
                               fh.read(), file_name=os.path.basename(caminho),
                               key=caminho)

st.divider()
st.subheader("What comes out")
R_previa = report.build(base, resultados, log=log)
components.table(export.index_table(R_previa))
st.caption("An empty table is not a defect: a scenario that reads the assembly "
           "from the factor table has no energy rows to report.")
