"""T05 · Dashboard — the results of a frozen run, every number with its seal."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import provenance
from ui import flow, navigation

ctx = flow.begin("Dashboard")
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    rs = flow.runs(conn, ida) if ida else []
    if not rs:
        st.info("No frozen run yet. Use **Validate and Freeze Inputs** (T41).")
        navigation.link("T41")
        st.stop()
    labels = {r["RunID"]: f"S{r['RunSeq']} · {r['FrozenAt']} · {r['Status']}" for r in rs}
    default = st.session_state.get("run_id")
    ids = list(labels)
    rid = st.selectbox("Run", ids, format_func=labels.get,
                       index=ids.index(default) if default in ids else len(ids) - 1)
    seq = next(r["RunSeq"] for r in rs if r["RunID"] == rid)
    st.info(flow.summary_phrase(conn, ida))
    df = pd.read_sql_query(
        "SELECT r.CaseKey, r.IDVPT, r.IDInd, i.DsInd, i.utInd, r.Value, r.ValueText, "
        "r.ValueOrigin FROM R45_PowertrainSummary r JOIN P51_OutputIndicator i "
        "ON i.IDInd = r.IDInd WHERE r.RunID = ? ORDER BY r.CaseKey, r.IDInd", conn, params=(rid,))

df["Seal"] = [provenance.label(flow.seal_of(o), seq) for o in df["ValueOrigin"]]
shown = df[df["ValueOrigin"].notna()]
st.subheader("Results")
table = shown.assign(Result=[
    f"{v:.6g}" if v == v and v is not None else (t or "")
    for v, t in zip(shown["Value"], shown["ValueText"])])
st.dataframe(table[["CaseKey", "IDVPT", "IDInd", "Result", "utInd", "Seal", "DsInd"]]
             .rename(columns={"IDVPT": "Powertrain", "IDInd": "Indicator", "DsInd": "Description",
                              "utInd": "Unit"}),
             hide_index=True, use_container_width=True)

st.subheader("Charts")
CHARTS = [("O20", "Vehicle weight"), ("O29", "Manufacturing GHG"),
          ("O12", "Combined power"), ("O19", "Battery energy")]
cols = st.columns(2)
for n, (ind, title) in enumerate(CHARTS):
    sub = shown[(shown["IDInd"] == ind) & shown["Value"].notna()]
    with cols[n % 2]:
        unit = sub["utInd"].iloc[0] if len(sub) else ""
        st.markdown(f"**{title}** ({unit})")
        if len(sub):
            st.bar_chart(sub.set_index("CaseKey")["Value"])
            st.caption(provenance.label(flow.seal_of(sub["ValueOrigin"].iloc[0]), seq))
        else:
            st.caption(provenance.NOT_AVAILABLE)
navigation.link("T18", "Details by group and material (T18)")
navigation.link("T08")
