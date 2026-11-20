"""T08 · Export — a run as tables (Excel, CSV, report) or as JSON, and the whole project.

The tables and the report follow the display format of T47 (decimal places, units, CSV
separators). The JSON is the canonical record: it always keeps the full precision.
"""

from __future__ import annotations

import os
import tempfile

import streamlit as st

from core import export, formatting, run, run_export
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
        st.subheader("The run as tables and report")
        fmt_ = flow.display_format(conn)
        st.caption("Follows the display format of T47: " + formatting.describe(fmt_)
                   + ". Excel keeps the full value in each cell and only formats it.")
        if st.button("Prepare Excel, CSV and report"):
            try:
                R, log = run.report_tables(conn, ctx.path, rid)
            except ValueError as exc:                          # I53
                st.error(str(exc))
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    files = {
                        "xlsx": export.to_xlsx(R, os.path.join(tmp, "r.xlsx"), fmt_),
                        "zip": export.to_csv_zip(R, os.path.join(tmp, "r.zip"), fmt=fmt_),
                        "html": export.to_html(R, os.path.join(tmp, "r.html"), fmt=fmt_)}
                    st.session_state["t08_files"] = (rid, {
                        k: open(v, "rb").read() for k, v in files.items()},
                        f"{len(log.of('ERRO'))} error(s), {len(log.of('AVISO'))} warning(s)")
        ready = st.session_state.get("t08_files")
        if ready and ready[0] == rid:
            st.caption("Validation of this run: " + ready[2])
            c1, c2, c3 = st.columns(3)
            c1.download_button("Excel (.xlsx)", ready[1]["xlsx"], file_name=f"{rid}.xlsx")
            c2.download_button("CSV (.zip)", ready[1]["zip"], file_name=f"{rid}.zip",
                               mime="application/zip")
            c3.download_button("Report (.html)", ready[1]["html"], file_name=f"{rid}.html",
                               mime="text/html")
            st.caption("To make a PDF, open the HTML report in the browser and print it.")
    else:
        st.info("No frozen run yet.")
    st.subheader("The project")
    proj = run_export.export_project(conn)
    st.caption(f"ExportHash `{proj['ExportHash']}` · {len(proj['runs'])} run(s)")
    st.download_button("Download project (JSON)", run_export.canonical(proj),
                       file_name=f"{ctx.ident['ProjectID']}.json", mime="application/json")
