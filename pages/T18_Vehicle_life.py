"""T18 · Vehicle life — cradle to gate, lifetime replacements and end of life.

One screen for the 0.9 Results screen and the 0.11 Vehicle life screen. The stages come from
C35 (and C15, C16) of a frozen run; the cradle-to-gate detail (by GREET group, material,
battery and assembly) is recalculated from the same frozen snapshot, so both always agree.
Cradle to gate is shown apart from replacements and end of life (I54); use of energy is not
here.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from core import charts, run
from core import formatting as fm
from ui import components, flow, navigation

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
    try:
        detail = run.recompute(conn, ctx.path, rid)
        detail_error = None
    except ValueError as exc:                                    # I53: lista mudou
        detail, detail_error = {}, str(exc)

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
keys = list(cases["CaseKey"])
_from_t05 = st.session_state.get("results_vehicle")
_names = dict(zip(cases["CaseKey"], cases["DsV"]))
_start = next((i for i, k in enumerate(keys) if _from_t05 in (k, _names[k])), 0)
case = st.selectbox("Vehicle", keys, index=_start,
                    format_func=lambda k: f"{k} · {_names[k]}")
one = life[life["CaseKey"] == case]
idcase = int(one["IDCase"].iloc[0])

res = detail.get(case, (None, None))[1]
if res is not None:
    _t = res["totals"]
    _c = st.columns(4)
    _c[0].metric("Vehicle mass (kg)", fm.fmt(_t["MassIDV"], "mass", FMT))
    _c[1].metric("Materials (kg CO₂e)", fm.fmt(_t["GHGMaterials"], "ghg", FMT))
    _c[2].metric("Assembly (kg CO₂e)", fm.fmt(_t["GHGAssembly"], "ghg", FMT))
    _c[3].metric("Cradle to gate (kg CO₂e)", fm.fmt(_t["GHGCradleToGate"], "ghg", FMT),
                 help=f"Assembly is included when the boundary is MAT_ASM. "
                      f"Boundary in use: {_t['Boundary']}.")
    components.coverage_note(_t)
elif detail_error:
    st.error(detail_error)


def _show(df):
    """Table in the project's display format (T47)."""
    classes = {c: fm.column_class(c) for c in df.columns if fm.column_class(c)}
    st.dataframe(fm.frame(df, classes, FMT, rename=True), hide_index=True,
                 use_container_width=True)


(tab_stage, tab_inv, tab_grp, tab_mat, tab_bat, tab_asm, tab_cmp, tab_trace) = st.tabs(
    ["Life stages", "Initial production", "By GREET group", "By material", "Battery",
     "Assembly", "Compare vehicles", "Traceability"])

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

with tab_grp:
    if res is None:
        st.info("Cradle-to-gate detail is not available for this run.")
    else:
        _c10 = res["C10"].sort_values("GHGIDGG", ascending=False)
        _steps = [(str(r.IDGG), float(r.GHGIDGG)) for r in _c10.itertuples()
                  if float(r.GHGIDGG) > 0]
        if res["totals"]["Boundary"] == "MAT_ASM" and res["totals"]["GHGAssembly"]:
            _steps.append(("Assembly", float(res["totals"]["GHGAssembly"])))
        components.chart(charts.waterfall(
            _steps, total_rotulo="Total", unidade="kg CO₂e",
            titulo=f"{_names[case]}: contribution of each GREET group"))
        components.how_was_this_calculated(
            "Emissions of one group",
            "GHG_group = Σ_materials  Mass_group × MshareGG × EF_material",
            {"Mass_group": "mass of the group (C02)",
             "MshareGG": "share of the material in the group (P16, by recipe)",
             "EF_material": "emission factor of the material (P11, by version)"}, "§12")
        _show(res["C10"])
        st.caption("Mass and emissions of every group, including the ones that "
                   "weigh nothing in this vehicle.")

with tab_mat:
    if res is None:
        st.info("Cradle-to-gate detail is not available for this run.")
    else:
        _show(res["C11"].sort_values("GHGIDM", ascending=False))
        if st.checkbox("Show the material × group detail, with shares and factors"):
            _show(res["C03"])
        if float(res["totals"].get("MassNoFactor") or 0) > 0:
            with st.expander("Which materials have mass but no emission factor?"):
                _v = res["C03"].assign(Part="Vehicle").rename(columns={"MassIDMpGG": "Mass (kg)"})
                _parts = [_v[["Part", "IDGG", "IDM", "DsM", "Mass (kg)", "HasFactor",
                              "CountsAsMass"]]]
                if len(res["C07"]):
                    _b = res["C07"].assign(Part="Battery").rename(
                        columns={"MassIDMpGGB": "Mass (kg)"})
                    _parts.append(_b[["Part", "IDGG", "IDM", "DsM", "Mass (kg)", "HasFactor",
                                      "CountsAsMass"]])
                _all = pd.concat(_parts, ignore_index=True)
                _miss = _all[(_all["CountsAsMass"] == 1) & (_all["HasFactor"] == 0)
                             & (_all["Mass (kg)"] > 0)]
                st.dataframe(_miss.drop(columns=["HasFactor", "CountsAsMass"]),
                             hide_index=True, use_container_width=True)
                st.caption("Choose another factor list in the project setup if one of "
                           "them publishes these materials.")

with tab_bat:
    if res is None:
        st.info("Cradle-to-gate detail is not available for this run.")
    elif not len(res["C07"]):
        st.info("This vehicle has no traction battery.")
    else:
        _show(res["C07"])

with tab_asm:
    if res is None:
        st.info("Cradle-to-gate detail is not available for this run.")
    else:
        _show(res["C13"])

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
