"""T01 · Home — projects, analysis type and the "How i3ET works" diagram (docs/06, T01)."""

from __future__ import annotations

import os
import shutil

import streamlit as st

from core import __version__, project
from ui import flow, navigation, state

flow.begin("Home", needs_project=False)
st.caption("Light vehicle carbon footprint, cradle to gate · modules M1 and M2 of the i3ET · "
           "NIPE/UNICAMP · kg CO₂e, GWP-100, IPCC AR6")

if not state.reference_exists():
    st.error("The reference database is missing. Build it with `python tools/make_db.py`.")
    st.stop()

left, right = st.columns([1.5, 1])
with left:
    st.subheader("Project")
    opened = state.project_path()
    if opened:
        with flow.connect(opened) as conn:
            if project.identity(conn) is None:
                project.create(conn, state.project_name())
            ident = project.identity(conn)
        flow.register(opened, ident["ProjectName"])
        st.success(f"**{ident['ProjectName']}** is open · `{ident['ProjectID']}`")
        with open(opened, "rb") as fh:
            st.download_button("Download project", fh.read(),
                               file_name=os.path.basename(opened),
                               mime="application/vnd.sqlite3")
        c2, c3 = st.columns([3, 1])
        new_name = c2.text_input("Name of the copy", value=f"{ident['ProjectName']}-copy")
        c3.write("")
        c3.write("")
        if c3.button("Save as"):
            dest = os.path.join(os.path.dirname(opened), state._slug(new_name) + ".sqlite")
            with flow.connect(opened) as conn:
                project.save_as(conn, dest, new_name)
            state._remember(dest, new_name)
            st.rerun()
        if st.button("Close project"):
            state.close_project()
            st.rerun()
        st.caption("Sessions in the cloud are temporary. Download the project to keep your work.")
    else:
        name = st.text_input("Name for a new project", value="my-project")
        if st.button("Create project", type="primary"):
            state.new_project(name)
            st.rerun()
        up = st.file_uploader("…or open an existing project (.sqlite)", type=["sqlite", "db"])
        if up is not None:
            try:
                state.open_uploaded(up)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        example = os.path.join(state.REPO, "data", "exemplo.sqlite")
        if os.path.exists(example) and st.button("Open example project (read-only)"):
            dest = state.new_project("example")
            shutil.copyfile(example, dest)
            st.rerun()

    st.subheader("Analysis type")
    st.radio("Analysis type", ["GHG (modules M1–M2)", "Energy (M3, planned)",
                               "Costs (M4, planned)", "Macroeconomic (M6, planned)"],
             label_visibility="collapsed",
             captions=["Mass and manufacturing emissions", "Available with M3",
                       "Available with M4", "Available with M6"],
             disabled=False, index=0, key="analysis_type",
             on_change=lambda: st.session_state.update(
                 analysis_type="GHG (modules M1–M2)"))

with right:
    st.subheader("Reference base")
    base = state.current_base()
    if base is not None:
        st.metric("Parameter hash", (base.param_hash or "")[:16])
        st.metric("Vehicles in the project", len(base["D01"]))
    st.metric("Program version", __version__)

BLOCKS = [
    ("Vehicle choice", "M1", "T02", "Pick market vehicles or a category."),
    ("Project configuration", "M1", "T03", "Mode, fuel, test norm, versions and combined power."),
    ("Selected parameters", "M1", "T04", "Control Panel parameters in three depths."),
    ("Vehicle parameters", "M1", "T10", "The values each vehicle is described by."),
    ("Default parameters", "M1", "T11", "Rules that fill in missing vehicle values."),
    ("Mass estimation (M1)", "M1", "T10", "Group masses and the material recipe."),
    ("Manufacturing GHG (M2)", "M2", "T18", "Materials and assembly emissions."),
    ("Emission factors", "M2", "T15", "Published versions, and your own."),
    ("Validate and freeze", "M1–M2", "T41", "Checks, then a frozen, hashed run."),
    ("Results", "M1–M2", "T05", "Dashboard, with a seal on every number."),
    ("Export", "M1–M2", "T08", "Run and project files, with their hash."),
]
st.subheader("How i3ET works")
st.caption("Open any block to see what it does and the screen where you can review it.")
cols = st.columns(3)
for n, (title, module, key, text) in enumerate(BLOCKS):
    with cols[n % 3]:
        with st.expander(f"{title} · {module}"):
            st.write(text)
            navigation.link(key)

st.divider()
st.caption("Emission factors derived from GREET © UChicago Argonne, LLC — redistributed for "
           "non-commercial use, input values modified (extracted and processed by the i3ET). "
           "Brazilian factors: Projeto do Berço ao Portão — FGV/Unicamp for Fundep, Programa Move.")
