"""T48 · Parameter review — the expert-block parameters with the periodic literature review.

Query only, independent of any project: ranges and adopted values come from the reference
base (P30); the review (P64, P65) adds the recommendation, the sources and the alerts. A
suggested value never reaches the calculation: to apply one, open Selected Parameters
(T04), which works on the values of your analysis. The workbook prevails and the
reference base is immutable.
New screen: it replaces the "I3et Parametros Expert" artifact and has no revised prototype.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

import pandas as pd
import streamlit as st

from core import param_review as pr
from ui import flow, navigation, state

flow.begin("Parameter review", needs_project=False)
ACTION_LABEL = {"keep": "Keep", "adjust": "Adjust", "verify": "Verify"}
TAG_LABEL = {"bat": "Battery", "ice": "Combustion engine"}


def _num(v) -> str:
    return "—" if v is None else f"{v:.6g}"


def _open_t04(idcp: str) -> None:
    st.session_state["t04_prefill"] = idcp
    st.switch_page(navigation.SCREENS["T04"][0])


# Consulta independente de projeto: tudo vem da base de referencia (P30, P64, P65).
with closing(sqlite3.connect(f"file:{state.REFERENCE_DB}?mode=ro", uri=True)) as conn:
    try:
        rows = pr.panel_rows(conn)
    except sqlite3.Error:
        rows = []
    if not rows:
        st.info("The reference base has no parameter review loaded.")
        st.stop()

    summary = pr.summary(rows)
    st.caption(
        f"Review of {summary['review_date']} · adopted values and ranges are those of the "
        "reference base; suggestions do not change any calculation. "
        "The workbook prevails.")
    m = st.columns(5)
    m[0].metric("Parameters", summary["total"])
    m[1].metric("Keep", summary["by_action"]["keep"])
    m[2].metric("Adjust", summary["by_action"]["adjust"])
    m[3].metric("Verify", summary["by_action"]["verify"])
    m[4].metric("Alerts", summary["alerts"])

    f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
    term = f1.text_input("Search parameter", placeholder="id, name or unit").strip().lower()
    blocks = f2.multiselect("Block", [b for b in pr.BLOCKS if any(r.section == b for r in rows)])
    actions = f3.multiselect("Recommendation", list(pr.ACTIONS), format_func=ACTION_LABEL.get)
    extra = f4.multiselect("Show only", ["Highlights", "Accepted", "Alerts", "Battery",
                                         "Combustion engine"])

    def _shown(r: pr.PanelRow) -> bool:
        if term and term not in " ".join([r.idcp, r.name, r.unit or ""]).lower():
            return False
        if blocks and r.section not in blocks:
            return False
        if actions and r.revision.action not in actions:
            return False
        checks = {"Highlights": r.revision.spotlight, "Accepted": r.revision.accepted,
                  "Alerts": bool(r.flags), "Battery": r.revision.tag == "bat",
                  "Combustion engine": r.revision.tag == "ice"}
        return all(checks[e] for e in extra)

    shown = [r for r in rows if _shown(r)]
    st.caption(f"{len(shown)} of {len(rows)} shown")

    table = pd.DataFrame([{
        "ID": r.idcp, "Block": r.section, "Parameter": r.name, "Unit": r.unit or "",
        "Minimum": _num(r.lo), "Most frequent": _num(r.mf), "Maximum": _num(r.hi),
        "Value": r.text if (r.value is None and r.text) else _num(r.value),
        "Recommendation": ACTION_LABEL[r.revision.action]
        + (f" ({pr.FIELD_LABEL[r.revision.field]} → {_num(r.revision.suggested)})"
           if r.revision.field and r.revision.suggested is not None else "")
        + (" · accepted" if r.revision.accepted else ""),
        "Alert": "; ".join(r.flags), "Note": r.note or "",
    } for r in shown])
    st.dataframe(table, hide_index=True, use_container_width=True)

    if not shown:
        st.stop()
    st.subheader("Parameter detail")
    labels = {r.idcp: f"{r.idcp} · {r.name}" for r in shown}
    pick = st.selectbox("Parameter", list(labels), format_func=labels.get,
                        key="review_pick")
    r = next(x for x in shown if x.idcp == pick)
    rev = r.revision
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(f"**{ACTION_LABEL[rev.action]}**"
                    + (f" · {TAG_LABEL[rev.tag]}" if rev.tag else "")
                    + (" · highlight" if rev.spotlight else ""))
        st.write(rev.rationale)
        if rev.caveat:
            st.caption(f"Caveat: {rev.caveat}")
        if rev.field and rev.suggested is not None:
            st.write(f"Suggested {pr.FIELD_LABEL[rev.field]}: **{_num(rev.suggested)}** "
                     f"(workbook at review time: {_num(rev.from_value)})"
                     + (f" — accepted on {rev.accepted_date}" if rev.accepted else ""))
        for flag in r.flags:
            st.warning(flag)
        if r.note:
            st.info(r.note)
    with c2:
        st.markdown("**Sources**")
        for ref, year in rev.sources:
            st.write(f"- {ref}" + (f" ({year})" if year else ""))
        past = pr.history(conn, r.idcp)[1:]
        if past:
            st.markdown("**Earlier reviews**")
            for h in past:
                st.write(f"- {h.review_date}: {ACTION_LABEL[h.action]}")
    if r.level == "X":
        st.caption("This is an Expanded-depth parameter: set the depth to Expanded in "
                   "Selected Parameters to edit it.")
    if st.button("Open in Selected Parameters", key="open_t04"):
        _open_t04(r.idcp)
