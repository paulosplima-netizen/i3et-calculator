"""T11 · Default parameters — the rules that fill in a vehicle's missing values."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import flow

ctx = flow.begin("Default parameters")
with flow.connect(ctx.path) as conn:
    versions = pd.read_sql_query("SELECT * FROM P49_DefaultRuleVersion", conn)
    st.dataframe(versions, hide_index=True, use_container_width=True)
    rules = pd.read_sql_query(
        "SELECT r.IDMP, p.DsMP, r.RuleSeq, r.IDVPT, r.IDVDT, r.IDVS, r.IDLR, r.PowerMinHP, "
        "r.PowerMaxHP, r.Value, r.ValueText, r.FactorOfIDMP FROM P35_VehicleParamDefaultRule r "
        "LEFT JOIN P54_MarketParam p ON p.IDMP = r.IDMP ORDER BY r.IDMP, r.RuleSeq", conn)
    st.caption(f"{len(rules)} rules (version TAB). Read-only: they are the reference.")
    summary = rules.groupby(["IDMP", "DsMP"], dropna=False).size().reset_index(name="Rules")
    st.dataframe(summary, hide_index=True, use_container_width=True)
    options = ["All"] + [f"{r.IDMP} · {r.DsMP}" for r in summary.itertuples()]
    chosen = st.selectbox("Inspect parameter", options)
    if chosen != "All":
        rules = rules[rules["IDMP"] == int(chosen.split(" · ")[0])]
    st.dataframe(rules, hide_index=True, use_container_width=True)
    comb = pd.read_sql_query("SELECT * FROM P53_CombinedPowerRule", conn)
    st.subheader("Combined power factors")
    st.dataframe(comb, hide_index=True, use_container_width=True)
