"""T03 · Project Configuration — mode, versions, cases, combined power (docs/06, T03)."""

from __future__ import annotations

import streamlit as st

from core import analysis, power_rule
from ui import flow, navigation

MAX_CASES = 7
ctx = flow.begin("Project Configuration", edit=True)

with flow.connect(ctx.path) as conn:
    cats = conn.execute("SELECT IDVC, DsVC FROM P29_VehicleCategory ORDER BY IDVC").fetchall()
    efvs = [r[0] for r in conn.execute("SELECT IDEFV FROM P10_EFVersion ORDER BY IDEFV")]
    apvs = [r[0] for r in conn.execute("SELECT IDAPV FROM P23_AssemblyParamVersion ORDER BY IDAPV")]
    mpvs = [r[0] for r in conn.execute(
        "SELECT DISTINCT IDMPV FROM P06_MassEstimationParam ORDER BY IDMPV")]
    market = {r[0]: r[1] for r in conn.execute(
        "SELECT IDMV, DsMV FROM P26_MarketVehicle ORDER BY IDMV")}

st.subheader("New analysis")
with st.form("new_analysis"):
    name = st.text_input("Analysis name", value="Analysis 1")
    mode = st.radio("Mode", ["EC", "FC"], horizontal=True,
                    captions=["Equalized comparison: six powertrains of one category",
                              "Free comparison: 1 to 7 market vehicles"])
    cat = st.selectbox("Category (EC)", [c[0] for c in cats],
                       format_func=dict(cats).get)
    picked = st.multiselect("Vehicles (FC)", list(market), format_func=market.get,
                            default=st.session_state.get("picked_idmv", []))
    c1, c2, c3 = st.columns(3)
    fuel = c1.text_input("Fuel scenario", value="E27")
    norm = c2.selectbox("Test norm", ["NBR", "EPA", "NEDC", "WLTC"])
    curve = c3.text_input("Distance curve", value="Default")
    d1, d2, d3 = st.columns(3)
    idefv = d1.selectbox("Emission factors", efvs,
                         index=efvs.index("BR23") if "BR23" in efvs else 0)
    idmpv = d2.selectbox("Mass parameters", mpvs)
    idapv = d3.selectbox("Assembly", apvs)
    e1, e2, e3 = st.columns(3)
    eco = e1.checkbox("SPHEV Eco")
    profile = e2.selectbox("Parameter profile", ["Basic", "Expert", "Expanded"], index=1)
    rule = e3.selectbox("Combined power rule", ["Default", "ExcelParity"],
                        format_func={"Default": "Default factors",
                                     "ExcelParity": "Excel parity"}.get)
    go = st.form_submit_button("Create analysis", type="primary", disabled=not ctx.can_edit)

if go:
    cfg = dict(fuel=fuel, norm=norm, curve=curve, idefv=idefv, idmpv=idmpv, idapv=idapv,
               sphev_eco=int(eco), profile=profile, power_rule=rule)
    try:
        with flow.connect(ctx.path) as conn:
            if mode == "EC":
                ida = analysis.create_ec(conn, name, cat, cfg)
            else:
                ida = analysis.create_fc(conn, name, cfg, [{"idmv": i} for i in picked],
                                         max_cases=MAX_CASES)
        st.session_state[flow.IDA_KEY] = ida
        st.rerun()
    except (ValueError, KeyError) as e:
        st.error(str(e))

st.divider()
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    if ida is not None:
        st.info(flow.summary_phrase(conn, ida))
        cases = conn.execute(
            "SELECT IDCase, CaseKey, CaseRole, IDVPT, SizingOrigin FROM D07_AnalysisVehicle "
            "WHERE IDA = ? ORDER BY IDCase", (ida,)).fetchall()
        st.subheader("Cases")
        st.dataframe([dict(zip(["Case", "Key", "Role", "Powertrain", "Sizing origin"], r))
                      for r in cases], hide_index=True, use_container_width=True)

        st.subheader("Combined power factors")
        st.caption("P = kICE·P_ICE + kEE·P_EE. Only HEV and PHEV take adjustments; "
                   "the others are fixed.")
        defaults = power_rule.load_defaults(conn)
        overrides = power_rule.load_overrides(conn, ida)
        for idcase, key, _, pt, _ in cases:
            if pt not in ("HEV", "PHEV"):
                continue
            cur = overrides.get(idcase) or defaults[pt]
            a, b, c, d = st.columns([2, 1, 1, 1])
            a.write(f"**{key} · {pt}** ({'custom' if idcase in overrides else 'default'})")
            k_ice = b.number_input("kICE", 0.0, 1.0, float(cur.ice), 0.05,
                                   key=f"kice{idcase}", disabled=not ctx.can_edit)
            k_ee = c.number_input("kEE", 0.0, 1.0, float(cur.ee), 0.05,
                                  key=f"kee{idcase}", disabled=not ctx.can_edit)
            if d.button("Save", key=f"sv{idcase}", disabled=not ctx.can_edit):
                power_rule.set_override(conn, ida, idcase, k_ice, k_ee)
                st.rerun()
            if idcase in overrides and d.button("Restore default", key=f"rs{idcase}",
                                                disabled=not ctx.can_edit):
                power_rule.clear_override(conn, ida, idcase)
                st.rerun()
        navigation.link("T04")
        navigation.link("T41")
