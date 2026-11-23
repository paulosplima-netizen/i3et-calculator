"""T40 · FENABRAVE import (master only).

Shows the licensing edition in the reference base (P48, P47) and matches a new FENABRAVE
bulletin (PDF or text) with the 154-vehicle catalogue. It lists the models that match exactly,
those split by powertrain, those whose units differ and those not in the catalogue. For models
that cover several powertrains it shows every candidate split side by side (reported by the
source, previous edition, PBEV versions); the master picks one or types the units, and saves
the edition. Source: FENABRAVE, Informativo Emplacamentos (all rights reserved; cite).
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
    # ---- divisao por motorizacao (decisao 9) e gravacao da edicao
    st.subheader("Split by powertrain")
    with master.reference_conn() as conn:
        anterior = (md.adopted_edition(conn, int(sec.period_end[:4]) - 1)
                    or md.adopted_edition(conn))
        linhas = md.split_candidates(conn, res, sec.rows, anterior)
    st.caption("One row per model and powertrain, never grouped. Candidates, in order of "
               "preference: reported by the source → previous edition → PBEV versions. Type "
               "units in “Units adopted” to override; the sum of a model must equal its "
               "bulletin total.")
    quadro = pd.DataFrame([{
        "IDMV": ln.idmv, "Model": ln.model, "Vehicle": ln.vehicle,
        "Powertrain": ln.powertrain, "Bulletin total": ln.pool_total,
        "Reported": ln.reported, "Previous edition": ln.previous, "PBEV versions": ln.pbev,
        "Method": ln.method, "Units adopted": ln.units, "Basis": ln.basis} for ln in linhas])
    so_dividir = st.checkbox("Only models with more than one powertrain", value=True)
    if so_dividir and not quadro.empty:
        conta = quadro.groupby("Model")["IDMV"].transform("count")
        visivel = quadro[conta > 1]
    else:
        visivel = quadro
    editado = st.data_editor(
        visivel, hide_index=True, use_container_width=True, key="split_editor",
        disabled=[c for c in visivel.columns if c != "Units adopted"])
    digitado = {int(r["IDMV"]): int(r["Units adopted"]) for _, r in editado.iterrows()
                if pd.notna(r["Units adopted"])}
    linhas = md.apply_master_units(linhas, digitado)
    problemas = md.validate_split(linhas)
    if problemas:
        st.error("The split does not add up: " + "; ".join(problemas))
    sem_par = [m for m in res if not m.idmvs]
    if sem_par:
        st.caption(f"{len(sem_par)} bulletin models have no match in the catalogue and are not "
                   "saved (decision 10): " + ", ".join(f"{m.row.brand} {m.row.model}"
                                                      for m in sem_par))
    novo_id = st.text_input("Edition ID", value=f"FEN{sec.period_end[:4]}_{sec.period_end[5:]}")
    st.caption("One series per year: the cumulative January-to-latest-month edition. Saving "
               "it replaces the adopted edition of the same year (the old one stays in the "
               "base as history). Months before December are marked as partial.")
    if st.button("Save edition to the reference base", disabled=bool(problemas)):
        try:
            with master.reference_write_conn() as wconn:
                n = md.save_edition(wconn, novo_id, sec, linhas, up.name, referencia=sec.title)
            st.success(f"Saved {n} rows as {novo_id}. On Streamlit Cloud the disk is "
                       "temporary: commit the reference base to publish it to other users.")
        except ValueError as exc:
            st.error(str(exc))
    import io
    buf = io.BytesIO()
    pd.DataFrame([ln.__dict__ for ln in linhas]).to_excel(buf, index=False)
    st.download_button("Export this split to Excel", buf.getvalue(),
                       file_name=f"{novo_id}_split.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
