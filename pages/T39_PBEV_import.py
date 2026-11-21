"""T39 · PBEV import (master only).

Shows the PBEV/INMETRO editions in the reference base and compares a new edition (the PDF
published by Inmetro) with the one in the base. It does not write: the comparison tells the
master what a new edition would add, remove or change. Source: PBEV/INMETRO (Creative Commons
BY-ND 3.0; cite the source and the edition).
"""

from __future__ import annotations

import os
import tempfile

import pandas as pd
import streamlit as st

from core import market_data as md
from ui import flow, master

flow.begin("PBEV import", needs_project=False)
master.require_master("PBEV import")

st.caption("Source: Programa Brasileiro de Etiquetagem Veicular (PBEV), INMETRO. Cite the "
           "source and the edition whenever these data are used.")
with master.reference_conn() as conn:
    ed = pd.read_sql_query("SELECT IDPBE AS Edition, EditionYear AS Year, EditionVersion AS "
                           "Version, RecordCount AS Records, SourcePBE AS Source FROM "
                           "P36_PBEVEdition", conn)
    linked = conn.execute("SELECT COUNT(DISTINCT IDMV) FROM P50_MarketVehiclePBEV").fetchone()[0]
    vehicles = conn.execute("SELECT COUNT(*) FROM P26_MarketVehicle WHERE IsSelecao = 0"
                            ).fetchone()[0]
st.subheader("Editions in the reference base")
st.dataframe(ed, hide_index=True, use_container_width=True)
st.caption(f"{linked} of {vehicles} market vehicles are linked to a PBEV record.")

st.subheader("Compare a new edition")
up = st.file_uploader("PBEV table (PDF from Inmetro)", type=["pdf"], key="pbev_pdf")
if up is not None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
        fh.write(up.getvalue())
        caminho = fh.name
    try:
        with st.spinner("Reading the table…"):
            registros = md.parse_pbev_rows(md.read_pdf_tables(caminho))
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()
    finally:
        os.unlink(caminho)
    dup = md.duplicate_keys(registros)
    with master.reference_conn() as conn:
        dif = md.diff_pbev(conn, registros, str(ed["Edition"].iloc[0]))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records in the file", len(registros))
    c2.metric("Added vs base", len(dif["added"]))
    c3.metric("Removed vs base", len(dif["removed"]))
    c4.metric("Energy use changed", len(dif["changed"]))
    st.caption(f"{len(dup)} keys repeat in the file (brand, model, version, engine, "
               "transmission). Names are compared after normalisation; spelling edits in the "
               "workbook appear as one added and one removed.")
    tab_a, tab_r, tab_c = st.tabs(["Added", "Removed", "Changed"])
    cols = ["Brand", "Model", "Version", "Engine", "Transmission"]
    for tab, chave in ((tab_a, "added"), (tab_r, "removed"), (tab_c, "changed")):
        with tab:
            st.dataframe(pd.DataFrame(dif[chave], columns=cols), hide_index=True,
                         use_container_width=True)
    st.info("Nothing was written. Importing an edition into the reference base waits for the "
            "author's decision on where imported editions are stored (docs/11, decision 5).")
