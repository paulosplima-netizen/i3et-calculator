"""T41 · Validate and Freeze Inputs — checklist, then a frozen, hashed run."""

from __future__ import annotations

import streamlit as st

from core import __version__, run
from ui import flow, navigation

ctx = flow.begin("Validate and Freeze Inputs", edit=True)
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    if ida is None:
        st.stop()
    st.info(flow.summary_phrase(conn, ida))
    problems = run.precheck(conn, ida)
    if problems:
        st.error(f"{len(problems)} problem(s) block the run.")
        for p in problems:
            st.write(f"- {p}")
    else:
        st.success("Every check passes. The inputs can be frozen.")
    pend = conn.execute("SELECT COUNT(*) FROM D07_AnalysisVehicle WHERE IDA=? AND "
                        "SizingOrigin='Pending'", (ida,)).fetchone()[0]
    if pend:
        st.warning(f"{pend} case(s) are Pending (no manufacturer data): they are not calculated.")
    wb = conn.execute("SELECT Value FROM M00_BaseInfo WHERE Key='FaseAWorkbook'").fetchone()
    if st.button("Freeze and run", type="primary", disabled=bool(problems) or not ctx.can_edit):
        rid = run.freeze(conn, ida, calculator_version=__version__,
                         reference_workbook=wb[0] if wb else "",
                         project_name=ctx.ident["ProjectName"])
        conn.commit()
        run.execute(conn, ctx.path, rid)
        st.session_state["run_id"] = rid
        st.success(f"Run `{rid}` frozen and calculated.")
        navigation.link("T05")
    previous = flow.runs(conn, ida)
    if previous:
        st.subheader("Previous runs")
        st.dataframe(previous, hide_index=True, use_container_width=True)
