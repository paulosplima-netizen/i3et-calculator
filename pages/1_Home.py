"""i3ET Calculator — cradle-to-gate carbon footprint of light vehicles.

Entry point of the web application. Each screen is a page under `pages/`, in
the order the analysis happens; this one is Home.

Run it with:

    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from core import __version__
from ui import components, state

st.set_page_config(page_title="i3ET Calculator", layout="wide",
                   initial_sidebar_state="expanded")

st.title("Light vehicle carbon footprint — cradle to gate")
st.caption("Modules M1 (mass) and M2 (manufacturing GHG) of the i3ET model · "
           "NIPE/UNICAMP · kg CO₂e, GWP-100, IPCC AR6")

if not state.reference_exists():
    st.error("The reference database is missing. Build it with "
             "`python tools/make_db.py`.")
    st.stop()

aberto = state.project_path()

esquerda, direita = st.columns([1.4, 1])

with esquerda:
    st.subheader("Project")
    st.write(
        "A project is one SQLite file: the reference parameters, plus your own "
        "vehicles, scenarios and emission factor versions. Creating one copies "
        "the reference base — you edit your copy, and the reference is never "
        "modified.")

    if aberto:
        st.success(f"**{state.project_name()}** is open.")
        with open(aberto, "rb") as fh:
            st.download_button("Download this project", fh.read(),
                               file_name=os.path.basename(aberto),
                               mime="application/vnd.sqlite3")
        st.caption("Sessions in the cloud are temporary. Download the project "
                   "to keep your work.")
        if st.button("Close project"):
            state.close_project()
            st.rerun()
    else:
        nome = st.text_input("Name for a new project", value="meu-projeto")
        if st.button("Create project", type="primary"):
            state.new_project(nome)
            st.rerun()

        enviado = st.file_uploader("…or open an existing project (.sqlite)",
                                   type=["sqlite", "db"])
        if enviado is not None:
            try:
                state.open_uploaded(enviado)
                st.rerun()
            except ValueError as e:
                st.error(str(e))

with direita:
    st.subheader("Reference base")
    base = state.current_base()
    if base is not None:
        st.metric("Parameter hash", (base.param_hash or "")[:16])
        st.metric("Vehicles in the project", len(base["D01"]))
        st.metric("Scenarios", len(base["D02"]))
    else:
        st.info("No project open yet.")
    st.metric("Program version", __version__)

if aberto:
    atual = state.current()
    if atual:
        st.divider()
        components.version_bar(atual[0], atual[2])
        st.divider()
        st.subheader("Where to go next")
        st.write(
            "1. **Vehicles** — the vehicles in the project, and your own\n"
            "2. **Vehicle parameters** — the values each vehicle is described by\n"
            "3. **Scenario** — which versions the calculation uses\n"
            "4. **Results** — mass and emissions, group by group and material "
            "by material\n"
            "5. **Emission factors** — the published versions, and your own\n"
            "6. **Export** — every table, in the format you need")

st.divider()
st.caption(
    "Emission factors derived from GREET © UChicago Argonne, LLC — "
    "redistributed for non-commercial use, input values modified (extracted "
    "and processed by the i3ET). Brazilian factors: Projeto do Berço ao Portão "
    "— FGV/Unicamp for Fundep, Programa Move.")
