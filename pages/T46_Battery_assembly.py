"""T46 · Battery and assembly — the registry the calculation already uses.

Read-only for the reference records. You can make an editable copy of a battery
model (prefix UB-) or of an assembly version (prefix UA-). A battery draft whose
groups do not close on 1 (or 0) cannot be used (I44). Generic batteries have no
composition (I45): mass = control parameter × power or energy.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import formatting as fm
from core import loader, user_assets
from ui import flow, navigation

ctx = flow.begin("Battery and assembly", edit=True)
author = st.sidebar.text_input("Your name", value=st.session_state.get("author", ""),
                               key="author")
with flow.connect(ctx.path) as conn:
    base = loader.load_sqlite(ctx.path)
    p19, p20, p09 = base["P19"], base["P20"], base["P09"]
    tab_b, tab_a, tab_g, tab_u = st.tabs(["Batteries", "Assembly", "Generic batteries",
                                          "Your copies"])

    with tab_b:
        kind = st.radio("Method", ["All", "composition", "gravimetric", "none"], horizontal=True)
        models = p19 if kind == "All" else p19[p19["GHGMethod"] == kind]
        cols = [c for c in ("IDBMd", "DsBMd", "IDEFV", "IDVPT", "IDBTe", "RefEnergy", "RefPower",
                            "RefWeight", "GHGMethod") if c in models.columns]
        st.dataframe(models[cols], hide_index=True, use_container_width=True)
        pick = st.selectbox("Composition of", list(models["IDBMd"]))
        comp = p20[p20["IDBMd"] == pick].merge(p09[["IDM", "DsM", "ShareRole"]], on="IDM")
        comp = comp[comp["BMshareGG"] > 0]
        fmt_ = flow.display_format(conn)
        share_col = f"Share ({fm.unit('share', fmt_) or 'fraction'})"
        comp[share_col] = fm.frame(comp, {"BMshareGG": "share"}, fmt_)["BMshareGG"]
        st.dataframe(comp[["IDGG", "IDM", "DsM", "ShareRole", share_col]], hide_index=True,
                     use_container_width=True)
        if len(comp) == 0:
            st.caption("No composition: this model is dimensioned by mass and carbon density.")

    with tab_a:
        st.dataframe(base["P23"], hide_index=True, use_container_width=True)
        st.dataframe(base["P21"], hide_index=True, use_container_width=True)
        apv = st.selectbox("Energy of version", list(base["P23"]["IDAPV"]))
        st.dataframe(base["P22"][base["P22"]["IDAPV"] == apv], hide_index=True,
                     use_container_width=True)
        st.caption("Process 1 (paint production) stays out of aggregate A of the i3ET.")

    with tab_g:
        st.dataframe(base["P58"], hide_index=True, use_container_width=True)
        st.caption("No composition; mass comes from the control parameters X72/X70/X67 "
                   "(edit them in T04).")

    with tab_u:
        if not ctx.can_edit:
            st.info("This project is read-only.")
        else:
            c1, c2 = st.columns(2)
            with c1.form("copy_battery"):
                st.markdown("**Copy a battery model**")
                ident = st.text_input("Identifier (starts with UB-)", value="UB-1")
                src = st.selectbox("Copy from", list(p19[p19["GHGMethod"] == "composition"]
                                                     ["IDBMd"]))
                name = st.text_input("Name")
                if st.form_submit_button("Create battery copy"):
                    try:
                        user_assets.copy_battery(conn, ident, src, name, author)
                        st.success(f"{ident} created.")
                    except ValueError as e:
                        st.error(str(e))
            with c2.form("copy_assembly"):
                st.markdown("**Copy an assembly version**")
                ident_a = st.text_input("Identifier (starts with UA-)", value="UA-1")
                src_a = st.selectbox("Copy from", list(base["P23"]["IDAPV"]))
                name_a = st.text_input("Name", key="na")
                if st.form_submit_button("Create assembly copy"):
                    try:
                        user_assets.copy_assembly(conn, ident_a, src_a, name_a, author)
                        st.success(f"{ident_a} created.")
                    except ValueError as e:
                        st.error(str(e))
        mine = pd.read_sql_query("SELECT IDBMdU, DsBMdU, IDBMdBase, UpdatedAt FROM "
                                 "D15_UserBatteryModel", conn)
        if len(mine):
            mine["Valid"] = [not user_assets.check_battery(conn, i) for i in mine["IDBMdU"]]
            st.dataframe(mine, hide_index=True, use_container_width=True)
            if ctx.can_edit:
                rid = st.selectbox("Edit battery copy", list(mine["IDBMdU"]))
                sh = pd.read_sql_query(
                    "SELECT d.IDGG, d.IDM, p.DsM, p.ShareRole, d.BMshareGG FROM "
                    "D16_UserBatteryShare d JOIN P09_Material p USING (IDM) WHERE "
                    "d.IDBMdU = ? AND d.BMshareGG > 0 ORDER BY d.IDGG, d.IDM", conn,
                    params=(rid,))
                ed = st.data_editor(sh, hide_index=True, use_container_width=True,
                                    disabled=["IDGG", "IDM", "DsM", "ShareRole"],
                                    key=f"edb_{rid}")
                if st.button("Save battery shares"):
                    try:
                        for o, n in zip(sh.itertuples(), ed.itertuples()):
                            if abs(o.BMshareGG - n.BMshareGG) > 1e-12:
                                user_assets.set_battery_share(conn, rid, n.IDGG, n.IDM,
                                                              float(n.BMshareGG))
                        problems = user_assets.check_battery(conn, rid)
                        (st.error if problems else st.success)(
                            "; ".join(problems) if problems else "Saved and valid.")
                    except ValueError as e:
                        st.error(str(e))
        st.dataframe(pd.read_sql_query("SELECT * FROM D17_UserAssemblyVersion", conn),
                     hide_index=True, use_container_width=True)

navigation.link("T04")
