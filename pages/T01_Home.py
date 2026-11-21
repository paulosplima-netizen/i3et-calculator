"""T01 · Home — projects, analysis type and the "How i3ET works" diagram (docs/06, T01)."""

from __future__ import annotations

import os
import shutil
import streamlit as st

from core import __version__, project
from ui import blocks, flow, navigation, state, storage, theme

flow.begin("Home", needs_project=False, show_title=False)
theme.inject()
blocks.hero(kicker="Integrated Economic, Energy and Environment Transport",
            title="Compare light vehicles across their life cycle",
            text="Configure a project, choose an analysis and trace each result to the "
                 "assumptions behind it.",
            types=[("Light Vehicles", True), ("Heavy Vehicles · future", False),
                   ("Fleet · future", False)])
st.caption("Light vehicle carbon footprint, cradle to gate · modules M1 and M2 of the i3ET · "
           "NIPE/UNICAMP · kg CO₂e, GWP-100, IPCC AR6")

if not state.reference_exists():
    st.error("The reference database is missing. Build it with `python tools/make_db.py`.")
    st.stop()

ANALYSES = {   # tipo de analise -> (tela de destino, situacao)
    "GHG LCA and LCC": ("T03", ""),
    "Sensitivity Analysis": ("T36", "planned: screen T36, a later phase"),
    "Monte Carlo": ("T37", "planned: screen T37, a later phase"),
    "Lightweighting": ("T32", "planned: screen T32, module M5"),
}
EXAMPLE = os.path.join(state.REPO, "data", "exemplo.sqlite")
EXAMPLE_NAME = "Excel Model LCA_LV_i3ET_20261119"      # master: nao se edita, so se copia


def _label(entry: dict) -> str:
    with flow.connect(entry["path"]) as conn:
        info = project.summary(conn)
    kind = {"EC": "EC", "FC": "FC"}.get(info["Mode"] or "", "no analysis")
    owner = "Master" if info["IsExample"] else "My project"
    return " · ".join([info["ProjectID"], info["ProjectName"], kind, owner])


def _open(path: str, name: str) -> None:
    state._remember(path, name)
    flow.register(path, name)


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

    # --- Select Project(s): a lista dos projetos abertos nesta sessao -------
    listed = st.session_state.get(flow.OPEN_KEY, [])
    if listed:
        st.markdown("**Select Project(s)**")
        picked = []
        for entry in listed:
            on = st.checkbox(_label(entry), key=f"sel_{entry['path']}",
                             value=entry["path"] in st.session_state.get(flow.SELECTED_KEY, []))
            if on:
                picked.append(entry["path"])
        st.session_state[flow.SELECTED_KEY] = picked
        if len(picked) == 1 and picked[0] != opened:
            if st.button("Open selection"):
                _open(picked[0], next(e["name"] for e in listed if e["path"] == picked[0]))
                st.rerun()
        if len(picked) > 1:
            st.info("Multiple projects selected. Parameters are read-only.")
            navigation.link("T06", "Compare selected projects")

    if opened:
        st.success(f"**{ident['ProjectName']}** is open · `{ident['ProjectID']}`")
        with open(opened, "rb") as fh:
            st.download_button("Download project", fh.read(),
                               file_name=os.path.basename(opened),
                               mime="application/vnd.sqlite3")
        if flow.selected_count() == 1 and not ident["IsExample"]:
            r1, r2 = st.columns([3, 1])
            new_title = r1.text_input("Rename selected project", value=ident["ProjectName"])
            r2.write("")
            r2.write("")
            if r2.button("Save name"):
                error = None
                try:
                    with flow.connect(opened) as conn:
                        project.rename(conn, new_title)
                except ValueError as e:
                    error = str(e)
                if error:
                    st.error(error)
                else:
                    st.session_state[state.NAME_KEY] = new_title.strip()
                    for p in st.session_state.get(flow.OPEN_KEY, []):
                        if p["path"] == opened:
                            p["name"] = new_title.strip()
                    st.rerun()
        c1, c2 = st.columns([3, 1])
        copy_name = c1.text_input("Name for the copy", key="copy_name",
                                  value=f"{ident['ProjectName']} (copy)",
                                  help="Works for your projects and for the read-only master "
                                       "example: the copy is yours and can be edited.")
        c2.write("")
        c2.write("")
        if c2.button("Save a copy"):
            if not copy_name.strip():
                st.error("Enter a name for the copy.")
            else:
                dest = storage.new_path(copy_name)
                with flow.connect(opened) as conn:
                    project.save_as(conn, dest, copy_name.strip())
                _open(dest, copy_name.strip())
                st.rerun()
        if st.button("Close project"):
            state.close_project()
            st.rerun()
        st.caption("Your project is saved in the projects folder." if storage.root()
                   else "Sessions in the cloud are temporary. Download the project to keep "
                        "your work.")

    # --- Project Configuration: criar, copiar, abrir -----------------------
    st.markdown("**Create project / Save as**")
    with st.form("new_project"):
        name = st.text_input("Name", value="my-project")
        mode = st.radio("Comparison mode", ["Equalized", "Free choice"], horizontal=True,
                        help="Equalized (EC): six powertrains of one category. "
                             "Free choice (FC): 1 to 7 market vehicles.")
        sources = {"Empty project": None}
        if os.path.exists(EXAMPLE):
            sources[EXAMPLE] = f"Master · {EXAMPLE_NAME}"
        sources.update({e["path"]: _label(e) for e in listed})
        source = st.selectbox("Copy from", list(sources),
                              format_func=lambda k: k if k == "Empty project" else sources[k])
        go = st.form_submit_button("Create project / Save as", type="primary")
    if go:
        if not name.strip():
            st.error("Enter a project name.")
        else:
            st.session_state["pref_mode"] = "EC" if mode == "Equalized" else "FC"
            if source == "Empty project":
                _open(state.new_project(name.strip()), name.strip())
            else:
                dest = storage.new_path(name)
                with flow.connect(source) as conn:
                    project.save_as(conn, dest, name.strip())
                _open(dest, name.strip())
            st.rerun()

    saved = storage.list_projects()
    if storage.root():
        st.markdown("**Saved projects**")
        st.caption(f"Folder: `{storage.root()}` · kept between sessions.")
        if saved:
            pick = st.selectbox("Open a saved project", saved, format_func=storage.label,
                                key="saved_pick")
            if st.button("Open saved project"):
                _open(pick["path"], pick["name"])
                st.rerun()
        else:
            st.caption("No saved project yet. Projects you create are saved here.")
    up = st.file_uploader("…or open an existing project (.sqlite)", type=["sqlite", "db"])
    # O seletor mantem o arquivo depois do st.rerun(): sem esta marca, cada recarga gravaria
    # uma copia nova na pasta de projetos (laco de 21/11/2026, 117 copias em 1 minuto).
    if up is not None and st.session_state.get("upload_done") != state.upload_token(up):
        try:
            st.session_state["upload_done"] = state.upload_token(up)
            _open(state.open_uploaded(up), os.path.splitext(up.name)[0])
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    if os.path.exists(EXAMPLE) and st.button(f"Open {EXAMPLE_NAME} (read-only)"):
        dest = state.new_project("example", persist=False)
        shutil.copyfile(EXAMPLE, dest)
        _open(dest, EXAMPLE_NAME)
        st.rerun()

    # --- Select Analysis Type ----------------------------------------------
    st.markdown("**Select Analysis Type**")
    kind = st.selectbox("Analysis", list(ANALYSES), key="analysis_type")
    target, status = ANALYSES[kind]
    ready = flow.selected_count() == 1 and opened and not status
    if status:
        st.caption(f"Not available yet — {status}.")
    elif not opened:
        st.caption("Open or create a project first.")
    if st.button("Open analysis", disabled=not ready):
        st.switch_page(navigation.SCREENS[target][0])
    st.caption("Advanced analyses use the cases in the selected project.")

with right:
    st.subheader("Reference base")
    base = state.current_base()
    if base is not None:
        st.metric("Parameter hash", (base.param_hash or "")[:16])
        st.metric("Vehicles in the project", len(base["D01"]))
    st.metric("Program version", __version__)

#: (titulo, descricao, tela de destino ou None, situacao do modulo)
#: Numeracao dos modulos como no i3ET em Excel (P30.UsedByModule): M3 energia, M4 uso
#: (perfil de uso e vida util), M5 leveza, M6 custo. Em conflito, vale o Excel.
COLUMNS = {
    "a": ("Inputs", [
        ("Vehicle design", "Dimensions, mass and aerodynamics", "T10", ""),
        ("Regional conditions", "Electricity, fuels and manufacturing", "T03", ""),
        ("Real-world use", "Driving, charging and service life", None, "M4, planned")]),
    "b": ("Model calculations", [
        ("Performance equivalence", "Comparison mode and targets", "T03", ""),
        ("Component sizing", "Power, range and batteries", "T03", ""),
        ("Vehicle mass", "Systems, materials and lightweighting", "T18", ""),
        ("Energy intensity", "Cycles, efficiency and energy flows", None, "M3, planned")]),
    "c": ("Outputs", [
        ("GHG emissions", "Manufacturing, use and end of life", "T18", "manufacturing only"),
        ("Life-cycle cost", "Cost assumptions and results", None, "M6, planned"),
        ("Energy use", "Fuel and electricity demand", None, "M3, planned"),
        ("Fleet model inputs", "Vehicle outputs for future fleet integration", None,
         "future")]),
}
st.subheader("How i3ET works")
st.caption("Open a block to go to the screen where you can review it. "
           "Blocks of later modules show their status.")
with st.container(key="i3-diagram"):
    cols = st.columns(3)
    for col, (tag, (label, nodes)) in zip(cols, COLUMNS.items()):
        with col:
            blocks.column_title(label)
            for n, (title, desc, target, status) in enumerate(nodes):
                with st.container(key=f"i3-node-{tag}-{n}"):
                    if target:
                        navigation.link(target, label=title)
                    else:
                        st.markdown(f"**{title}**")
                    st.caption(desc + (f" · {status}" if status else ""))

st.divider()
st.caption("Emission factors derived from GREET © UChicago Argonne, LLC — redistributed for "
           "non-commercial use, input values modified (extracted and processed by the i3ET). "
           "Brazilian factors: Projeto do Berço ao Portão — FGV/Unicamp for Fundep, Programa Move.")
