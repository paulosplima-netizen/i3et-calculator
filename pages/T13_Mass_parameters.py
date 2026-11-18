"""T13 · Mass parameters — MR, GCR and β of each subsystem.

    ME = MR × (GC / GCR)^β × fLM

The reference set is read-only. You can copy it (prefix UM-) and edit MR, GCR, β and
fLM; the preview shows the effect before anything is used. Rule I58: MR ≥ 0, GCR > 0,
fLM ≥ 0. The two consumables (rows 54 and 55) stay neutral (GCR = 1, MR = 0).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import loader, user_mass_params
from ui import flow, navigation

ctx = flow.begin("Mass parameters", edit=True)
author = st.sidebar.text_input("Your name", value=st.session_state.get("author", ""),
                               key="author")
with flow.connect(ctx.path) as conn:
    base = loader.load_sqlite(ctx.path)
    versions = base["P05"]
    chosen = st.selectbox("Version", list(versions["IDMPV"]), format_func=lambda v: (
        f"{v} · {versions.set_index('IDMPV').loc[v, 'DsMPV']}"))
    table = (base["P06"][base["P06"]["IDMPV"] == chosen]
             .merge(base["P02"], on="IDSG").merge(base["P08"][["IDSG", "IDVP", "IDGG"]],
                                                  on="IDSG", how="left"))
    st.dataframe(table[["IDSG", "DsSG", "IDGG", "IDVP", "MR", "GCR", "utGCR", "Beta", "fLM",
                        "Reference"]], hide_index=True, use_container_width=True)

    st.subheader("Preview")
    row = st.selectbox("Subsystem", list(table["IDSG"]), format_func=lambda s: (
        f"{s} · {table.set_index('IDSG').loc[s, 'DsSG']}"))
    r = table[table["IDSG"] == row].iloc[0]
    gc = st.number_input("GC (value of the vehicle parameter)", min_value=0.0,
                         value=float(r["GCR"]))
    me = user_mass_params.preview(r["MR"], gc, r["GCR"], r["Beta"], r["fLM"])
    st.metric("ME (kg)", f"{me:,.1f}")

    st.subheader("Your copies")
    if ctx.can_edit:
        with st.form("copy_mpv"):
            c1, c2 = st.columns(2)
            ident = c1.text_input("Identifier (starts with UM-)", value="UM-1")
            src = c2.selectbox("Copy from", list(versions[~versions["IDMPV"].astype(str)
                                                         .str.startswith("UM-")]["IDMPV"]))
            name = st.text_input("Name")
            if st.form_submit_button("Create copy"):
                try:
                    user_mass_params.copy_version(conn, ident, int(src), name, author)
                    st.success(f"{ident} created.")
                except ValueError as e:
                    st.error(str(e))
    mine = pd.read_sql_query("SELECT IDMPVU, DsMPVU, IDMPVBase, CreatedAt FROM "
                             "D20_UserMassParamVersion", conn)
    st.dataframe(mine, hide_index=True, use_container_width=True)
    if len(mine) and ctx.can_edit:
        mid = st.selectbox("Edit copy", list(mine["IDMPVU"]))
        sub = pd.read_sql_query(
            "SELECT d.IDSG, p.DsSG, d.MR, d.GCR, d.Beta, d.fLM, d.Reference FROM "
            "D21_UserMassParam d JOIN P02_VehicleSubgroup p USING (IDSG) WHERE d.IDMPVU = ? "
            "ORDER BY d.IDSG", conn, params=(mid,))
        ed = st.data_editor(sub, hide_index=True, use_container_width=True,
                            disabled=["IDSG", "DsSG"], key=f"edm_{mid}")
        if st.button("Save parameters"):
            try:
                for o, n in zip(sub.itertuples(index=False), ed.itertuples(index=False)):
                    if tuple(o[2:6]) != tuple(n[2:6]) or o.Reference != n.Reference:
                        user_mass_params.set_param(
                            conn, mid, int(n.IDSG), beta=float(n.Beta), gcr=float(n.GCR),
                            mr=float(n.MR), flm=float(n.fLM), reference=n.Reference or "",
                            author=author)
                st.success("Saved.")
            except ValueError as e:
                st.error(str(e))

navigation.link("T12")
