"""T08 · Export — a run, or the whole project, as JSON with its hash."""

from __future__ import annotations

import streamlit as st

from core import run_export
from ui import flow

ctx = flow.begin("Export")
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    rs = flow.runs(conn, ida) if ida else []
    st.subheader("A run")
    if rs:
        ids = [r["RunID"] for r in rs]
        rid = st.selectbox("Run", ids, index=len(ids) - 1)
        payload = run_export.export_run(conn, rid)
        problems = run_export.verify(payload)
        if problems:
            st.error("; ".join(problems))
        st.caption(f"ProjectID `{payload['project']['ProjectID']}` · RunID `{rid}` · "
                   f"ExportHash `{payload['ExportHash']}` · previews omitted: "
                   f"{payload['omitted_previews']}")
        st.download_button("Download run (JSON)", run_export.canonical(payload),
                           file_name=f"{rid}.json", mime="application/json")
    else:
        st.info("No frozen run yet.")
    st.subheader("The project")
    proj = run_export.export_project(conn)
    st.caption(f"ExportHash `{proj['ExportHash']}` · {len(proj['runs'])} run(s)")
    st.download_button("Download project (JSON)", run_export.canonical(proj),
                       file_name=f"{ctx.ident['ProjectID']}.json", mime="application/json")
