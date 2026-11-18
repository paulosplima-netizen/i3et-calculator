"""T02 · Vehicle picker — the P26 catalog, with filters (docs/06, T02)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import flow, navigation

PICK_KEY = "picked_idmv"

ctx = flow.begin("Vehicle picker")
with flow.connect(ctx.path) as conn:
    df = pd.read_sql_query(
        "SELECT IDMV, DsMV, Brand, Model, IDVPT AS Powertrain, IDVDT AS Body, IDVS AS Size, "
        "IDLR AS Luxury, Fuel, MarketGroup, SalesUnits FROM P26_MarketVehicle ORDER BY IDMV",
        conn)

f1, f2, f3, f4 = st.columns(4)
pt = f1.multiselect("Powertrain", sorted(df["Powertrain"].dropna().unique()))
body = f2.multiselect("Body", sorted(df["Body"].dropna().unique()))
size = f3.multiselect("Size", sorted(df["Size"].dropna().unique()))
text = f4.text_input("Search make or model", placeholder="e.g. Fiat, Dolphin")
sel = df
for col, vals in (("Powertrain", pt), ("Body", body), ("Size", size)):
    if vals:
        sel = sel[sel[col].isin(vals)]
if text:
    mask = sel["Brand"].fillna("").str.contains(text, case=False) | \
        sel["Model"].fillna("").str.contains(text, case=False)
    sel = sel[mask]

st.caption(f"{len(sel)} of {len(df)} vehicles · SalesUnits: licensings of the reference year "
           "(FENABRAVE public reports, cumulative January to December; see data/NOTICE.md)")
chosen = st.session_state.get(PICK_KEY, [])
table = sel.assign(Pick=sel["IDMV"].isin(chosen))
edited = st.data_editor(table, hide_index=True, use_container_width=True, key="picker_editor",
                        disabled=[c for c in table.columns if c != "Pick"])
picked = sorted(set(chosen) - set(sel["IDMV"]) | set(edited.loc[edited["Pick"], "IDMV"]))
st.session_state[PICK_KEY] = picked
st.write(f"**Picked:** {len(picked)} (a free comparison takes 1 to 7)")
navigation.link("T03")
