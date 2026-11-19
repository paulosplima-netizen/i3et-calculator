"""T03 · Project Configuration — mode, versions, cases, combined power (docs/06, T03)."""

from __future__ import annotations

import streamlit as st

from core import analysis, power_rule
from ui import flow, navigation

MAX_CASES = 7
ctx = flow.begin("Project Configuration", edit=True)

with flow.connect(ctx.path) as conn:
    cats = conn.execute("SELECT IDVC, DsVC FROM P29_VehicleCategory ORDER BY IDVC").fetchall()
    # your own copies (T15, T46, T13) can be chosen next to the reference ones
    efvs = [r[0] for r in conn.execute(
        "SELECT IDEFV FROM P10_EFVersion UNION SELECT IDEFV FROM D04_UserEFVersion "
        "ORDER BY IDEFV")]
    apvs = [r[0] for r in conn.execute(
        "SELECT IDAPV FROM P23_AssemblyParamVersion UNION SELECT IDAPVU FROM "
        "D17_UserAssemblyVersion ORDER BY 1")]
    mpvs = [r[0] for r in conn.execute(
        "SELECT DISTINCT IDMPV FROM P06_MassEstimationParam ORDER BY IDMPV")] + [
        r[0] for r in conn.execute("SELECT IDMPVU FROM D20_UserMassParamVersion ORDER BY 1")]
    market = {r[0]: r[1] for r in conn.execute(
        "SELECT IDMV, DsMV FROM P26_MarketVehicle ORDER BY IDMV")}

st.subheader("New analysis")
# O modo fica fora do formulario: trocar de modo reexecuta a pagina e mostra so os
# campos que valem para ele (categoria no EC; veiculos no FC).
mode = st.radio("Mode", ["EC", "FC"], horizontal=True, key="new_mode",
                index=0 if st.session_state.get("pref_mode", "EC") == "EC" else 1,
                captions=["Equalized comparison: six powertrains of one category",
                          "Free comparison: 1 to 7 market vehicles"])
with st.form("new_analysis"):
    name = st.text_input("Analysis name", value="Analysis 1")
    if mode == "EC":
        cat = st.selectbox("Category (EC)", [c[0] for c in cats], format_func=dict(cats).get)
        picked = []
    else:
        cat = None
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

        st.subheader("Material recipe per case")
        st.caption("The recipe sets the material shares of each vehicle. SHEV uses the HEV "
                   "recipes and SPHEV the PHEV ones. A frozen run keeps what it froze; the "
                   "next run freezes the new choice.")
        for idcase, key, _, pt, _ in cases:
            options = analysis.case_recipe_options(conn, ida, idcase)
            current = analysis.case_recipe(conn, ida, idcase)
            a, b = st.columns([1, 3])
            a.write(f"**{key} · {pt}**")
            pick = b.selectbox("Recipe", options, key=f"rcp{ida}_{idcase}",
                               index=options.index(current) if current in options else 0,
                               label_visibility="collapsed", disabled=not ctx.can_edit)
            if pick != current and ctx.can_edit:
                analysis.set_recipe(conn, ida, idcase, pick)
                st.rerun()

        st.subheader("Combined power factors")
        st.caption("P = kICE·P_ICE + kEE·P_EE. Only HEV and PHEV take adjustments; "
                   "the others are fixed.")
        defaults = power_rule.load_defaults(conn)
        st.dataframe([{"Powertrain": pt, "kICE": f.ice, "kEE": f.ee,
                       "Adjustable": "no" if pt in power_rule.FIXED_POWERTRAINS else "yes",
                       "Provisional": "yes" if f.provisional else "no"}
                      for pt, f in defaults.items()],
                     hide_index=True, use_container_width=True)
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
