"""T18 · Vehicle life — initial production, lifetime replacements and end of life.

Reads C35 (and C15, C16) of a frozen run. Cradle-to-gate (initial production) is
shown apart from replacements and end of life (I54). Use of energy is not here.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from ui import flow, navigation

STAGE_NAMES = {"INITIAL_PRODUCTION": "Initial production (cradle to gate)",
               "LIFETIME_REPLACEMENTS": "Lifetime replacements",
               "END_OF_LIFE": "End of life"}

ctx = flow.begin("Vehicle life")
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    rs = flow.runs(conn, ida) if ida else []
    if not rs:
        st.info("No frozen run yet. Use **Validate and Freeze Inputs** (T41).")
        navigation.link("T41")
        st.stop()
    labels = {r["RunID"]: f"S{r['RunSeq']} · {r['FrozenAt']} · {r['Status']}" for r in rs}
    ids = list(labels)
    default = st.session_state.get("run_id")
    rid = st.selectbox("Run", ids, format_func=labels.get,
                       index=ids.index(default) if default in ids else len(ids) - 1)
    FMT = flow.display_format(conn)
    life = pd.read_sql_query(
        "SELECT c.IDCase, a.CaseKey, v.DsV, c.Stage, c.SubStage, c.GHGkg, c.SourceCell, "
        "c.Method, c.Note FROM C35_VehicleLifeStage c "
        "JOIN D07_AnalysisVehicle a ON a.IDA = c.IDA AND a.IDCase = c.IDCase "
        "JOIN D01_Vehicle v ON v.IDV = c.IDV WHERE c.RunID = ? ORDER BY c.IDCase", conn,
        params=(rid,))
    eol = pd.read_sql_query(
        "SELECT IDCase, EoLMethod, GliderMassKg, BatteryKWh, FactorGlider, FactorBattery, "
        "FactorVehicle, GHGEoL FROM C16_EndOfLife WHERE RunID = ?", conn, params=(rid,))
    repl = pd.read_sql_query(
        "SELECT IDCase, IDMI, COUNT(*) AS Events, MIN(EventKm) AS FirstKm, SUM(GHGkg) AS GHGkg "
        "FROM C15_Replacement WHERE RunID = ? GROUP BY IDCase, IDMI", conn, params=(rid,))

if life.empty:
    st.info("This run has no vehicle-life results (it was run before version 0.11).")
    st.stop()

st.warning("This is not the full life-cycle footprint: the supply and use of fuel and "
           "electricity belong to the use-phase results (M4). Replacements and end of life "
           "are always shown apart from cradle to gate.")
_fmt = FMT
_units = ["kg CO₂e / vehicle", "t CO₂e / vehicle"]
tonnes = st.radio("Unit", _units, index=1 if _fmt.ghg_unit == "t" else 0,
                  horizontal=True) != _units[0]
_d = _fmt.decimals["ghg"]
factor, digits = (0.001, 6 if _d is None else _d + (2 if _fmt.ghg_unit == "kg" else 0)) \
    if tonnes else (1.0, 6 if _d is None else _d)
_sd = 6 if _fmt.decimals["share"] is None else _fmt.decimals["share"]
unit = "t CO₂e" if tonnes else "kg CO₂e"

cases = life[["CaseKey", "DsV"]].drop_duplicates()
case = st.selectbox("Vehicle", cases["CaseKey"],
                    format_func=lambda k: f"{k} · {cases.set_index('CaseKey').loc[k, 'DsV']}")
one = life[life["CaseKey"] == case]
idcase = int(one["IDCase"].iloc[0])

tab_stage, tab_inv, tab_cmp, tab_trace = st.tabs(
    ["Life stages", "Manufacturing breakdown", "Compare vehicles", "Traceability"])

with tab_stage:
    per = one.groupby("Stage")["GHGkg"].sum()
    total = float(per.sum())
    rows = [{"Stage": STAGE_NAMES[s], f"GHG ({unit})": round(float(per.get(s, 0.0)) * factor,
                                                             digits),
             "Share (%)": round(100 * float(per.get(s, 0.0)) / total, _sd) if total else 0.0}
            for s in STAGE_NAMES]
    rows.append({"Stage": "Vehicle life, without use of energy",
                 f"GHG ({unit})": round(total * factor, digits), "Share (%)": 100.0})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    bars = pd.DataFrame({"Stage": [STAGE_NAMES[s] for s in STAGE_NAMES],
                         "GHG": [float(per.get(s, 0.0)) * factor for s in STAGE_NAMES]})
    st.altair_chart(alt.Chart(bars).mark_bar().encode(
        x=alt.X("Stage:N", sort=None, title=None), y=alt.Y("GHG:Q", title=unit),
        tooltip=["Stage", "GHG"]), use_container_width=True)

with tab_inv:
    ini = one[one["Stage"] == "INITIAL_PRODUCTION"].copy()
    ini[f"GHG ({unit})"] = (ini["GHGkg"] * factor).round(digits)
    st.dataframe(ini[["SubStage", f"GHG ({unit})", "SourceCell", "Method", "Note"]],
                 hide_index=True, use_container_width=True)

with tab_cmp:
    wide = (life.groupby(["CaseKey", "Stage"])["GHGkg"].sum().unstack(fill_value=0.0)
            .reindex(columns=list(STAGE_NAMES), fill_value=0.0))
    wide["Total"] = wide.sum(axis=1)
    st.dataframe((wide * factor).round(digits).rename(columns=STAGE_NAMES),
                 use_container_width=True)

with tab_trace:
    e = eol[eol["IDCase"] == idcase]
    if len(e):
        st.markdown(f"**End-of-life method:** `{e['EoLMethod'].iloc[0]}`")
        st.dataframe(e.drop(columns="IDCase"), hide_index=True, use_container_width=True)
    r = repl[repl["IDCase"] == idcase]
    st.markdown("**Replacements used**")
    if len(r):
        st.dataframe(r.drop(columns="IDCase"), hide_index=True, use_container_width=True)
    else:
        st.caption("No replacement events (maintenance off or life shorter than every interval).")

st.download_button("Download CSV", life.drop(columns="IDCase").to_csv(index=False),
                   file_name=f"vehicle_life_{rid}.csv", mime="text/csv")
navigation.link("T05")
