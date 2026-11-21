"""T40 · FENABRAVE import (master only).

Shows the licensing edition in the reference base (P48, P47) and matches a new FENABRAVE
bulletin (PDF or text) with the 154-vehicle catalogue. It does not write: it lists the models
that match exactly, those split by powertrain, those whose units differ and those not in the
catalogue. Source: FENABRAVE, Informativo Emplacamentos (all rights reserved; cite).
"""

from __future__ import annotations

import os
import tempfile

import pandas as pd
import streamlit as st

from core import market_data as md
from ui import flow, master

flow.begin("FENABRAVE import", needs_project=False)
master.require_master("FENABRAVE import")

st.caption("Source: FENABRAVE, Informativo Emplacamentos. Cite the source and the period "
           "whenever these data are used.")
with master.reference_conn() as conn:
    ed = pd.read_sql_query(
        "SELECT IDMSE AS Edition, PeriodKind AS Kind, PeriodStart AS Start, PeriodEnd AS End, "
        "EditionRef AS Bulletin, RecordCount AS Records, IsAdopted AS Adopted FROM "
        "P48_MarketSalesEdition", conn)
    sales = pd.read_sql_query(
        "SELECT s.SalesClass AS Class, s.Ranking AS Rank, s.Brand, s.Model, "
        "s.UnitsSource AS \"Units (source)\", s.UnitsAdopted AS \"Units (adopted)\", "
        "s.AdjustmentNote AS Adjustment, v.IDVPT AS Powertrain FROM P47_MarketSales s "
        "LEFT JOIN P26_MarketVehicle v USING (IDMV) ORDER BY s.SalesClass DESC, s.Ranking",
        conn)
st.subheader("Editions in the reference base")
st.dataframe(ed, hide_index=True, use_container_width=True)
adj = sales[sales["Units (source)"] != sales["Units (adopted)"]]
st.caption(f"{len(sales)} models; {len(adj)} with units redistributed by the author between "
           "powertrains (adopted ≠ source).")
tab_all, tab_adj = st.tabs(["All models", "Adjusted by the author"])
with tab_all:
    st.dataframe(sales, hide_index=True, use_container_width=True)
with tab_adj:
    st.dataframe(adj, hide_index=True, use_container_width=True)

st.subheader("Match a new bulletin")
up = st.file_uploader("FENABRAVE bulletin (PDF or text)", type=["pdf", "txt"], key="fen_file")
if up is not None:
    if up.name.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(up.getvalue())
            caminho = fh.name
        try:
            texto = md.read_pdf_text(caminho)
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()
        finally:
            os.unlink(caminho)
    else:
        texto = up.getvalue().decode("utf-8", errors="replace")
    secoes = md.parse_fenabrave_text(texto)
    if not secoes:
        st.warning("No “Ranking dos emplacamentos” table was found in the file.")
        st.stop()
    opcoes = {f"{s.kind} up to {s.period_end} ({len(s.rows)} rows)": s for s in secoes}
    padrao = md.adopted_section(secoes)
    nomes = list(opcoes)
    escolha = st.selectbox("Table", nomes,
                           index=nomes.index(next(n for n, s in opcoes.items() if s is padrao))
                           if padrao else 0)
    sec = opcoes[escolha]
    with master.reference_conn() as conn:
        res = md.match_to_catalog(conn, sec.rows)
    por = {}
    for m in res:
        por[m.row.sales_class + "/" + m.status] = por.get(m.row.sales_class + "/" + m.status,
                                                          0) + 1
    cols = st.columns(4)
    for c, status in zip(cols, ("exact", "split", "differs", "none"), strict=True):
        c.metric({"exact": "Exact match", "split": "Split by powertrain",
                  "differs": "Units differ", "none": "Not in catalogue"}[status],
                 sum(n for k, n in por.items() if k.endswith("/" + status)))
    tabela = pd.DataFrame([{
        "Class": m.row.sales_class, "Rank": m.row.ranking,
        "Brand": m.row.brand, "Model": m.row.model, "Bulletin units": m.row.units,
        "Catalogue units": m.catalog_units, "Status": m.status,
        "Catalogue IDs": ", ".join(map(str, m.idmvs))} for m in res])
    mostrar = st.radio("Show", ["Needs attention", "All"], horizontal=True)
    if mostrar == "Needs attention":
        tabela = tabela[tabela["Status"].isin(["differs", "none"])]
    st.dataframe(tabela, hide_index=True, use_container_width=True)
    st.info("Nothing was written. “Split” rows need the powertrain shares (the workbook keeps "
            "them by hand in its Powertrain breakdown sheet); see docs/11, decision 9.")
