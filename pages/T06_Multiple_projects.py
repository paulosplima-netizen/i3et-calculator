"""T06 · Multiple Projects — runs of several projects side by side, read-only."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import formatting as fm
from core import provenance
from ui import flow

flow.begin("Multiple Projects", needs_project=False)
opened = st.session_state.get(flow.OPEN_KEY, [])
if not opened:
    st.info("Open a project on **Home** first; projects opened in this session appear here.")
    st.stop()
names = {p["path"]: p["name"] for p in opened}
chosen = st.multiselect("Projects", list(names), format_func=names.get,
                        default=st.session_state.get(flow.SELECTED_KEY, []))
st.session_state[flow.SELECTED_KEY] = chosen
if len(chosen) >= 2:
    st.info("Several projects are selected: all are read-only on the other screens.")
frames = []
for path in chosen:
    with flow.connect(path) as conn:
        df = pd.read_sql_query("SELECT * FROM R46_RunComparison", conn)
        fmt_ = flow.display_format(conn)          # each project keeps its own T47 format
    shown = [fm.indicator(v, u, fmt_) for v, u in zip(df["Value"], df["utInd"])]
    df["Value"] = [t if t else (vt or "") for (t, _), vt in zip(shown, df["ValueText"])]
    df["utInd"] = [u for _, u in shown]
    df = df.drop(columns=["ValueText"])
    df.insert(0, "Project", names[path])
    frames.append(df)
if frames:
    all_ = pd.concat(frames, ignore_index=True)
    all_["Seal"] = [provenance.label(flow.seal_of(o), s)
                    for o, s in zip(all_["ValueOrigin"], all_["RunSeq"])]
    st.dataframe(all_.drop(columns=["ValueOrigin"]), hide_index=True, use_container_width=True)
