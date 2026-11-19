"""T38 · Mass validation — the declared mass against the estimated mass.

The estimated subsystem masses (owner's-manual parameters, betas and reference
masses) split the vehicle among material-recipe groups. The gap to the declared
total mass is allocated to Body and Chassis, the systems most subject to
customization: Body gets s·Adj and Chassis (1−s)·Adj. By default s is the Body share of
the estimated masses, so the final Body/Chassis proportion equals the estimated one. The
GREET proportion (P63) is only a reference: it shows how far the estimate is from it.
Saved on D07; it takes effect in the next frozen run (T41).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import b1_choices
from ui import flow, navigation

ctx = flow.begin("Mass validation", edit=True)
st.caption("Basis: vehicle without driver and without fuel. A manufacturer's declared mass "
           "often includes a 75 kg driver or fuel.")
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    if ida is None:
        st.stop()
    cases = pd.read_sql_query(
        "SELECT a.IDCase, a.CaseKey, a.CaseRole, v.DsV, a.DeclaredMassKg, a.MassAdjustmentKg, "
        "a.MassBodyShare, a.DeclaredSource, d.IDVMR FROM D07_AnalysisVehicle a "
        "JOIN D01_Vehicle v ON v.IDV = a.IDV JOIN D02_EvaluationAlternative d "
        "ON d.IDV = a.IDV AND d.IDEA = a.IDEA WHERE a.IDA = ? ORDER BY a.IDCase", conn,
        params=(ida,))
    if cases.empty:
        st.info("This analysis has no vehicles yet.")
        st.stop()
    rs = flow.runs(conn, ida)
    last = rs[-1]["RunID"] if rs else None
    c34 = pd.read_sql_query(
        "SELECT IDCase, MassBasis, DeclaredMassKg, CalculatedMassKg, DiffKg, DiffPct, "
        "AdjustmentKg, ResidualKg, BodyShare, BodyShareEstimated, BodyShareReference "
        "FROM C34_MassValidation WHERE RunID = ?",
        conn, params=(last,)) if last else pd.DataFrame()

    st.subheader("Vehicles")
    summary = cases.merge(c34[["IDCase", "CalculatedMassKg"]], on="IDCase", how="left") \
        if len(c34) else cases.assign(CalculatedMassKg=None)
    summary["Gap (kg)"] = summary["DeclaredMassKg"] - summary["CalculatedMassKg"]
    summary["Gap (%)"] = 100 * summary["Gap (kg)"] / summary["CalculatedMassKg"]
    st.dataframe(summary[["CaseKey", "CaseRole", "DsV", "DeclaredMassKg", "CalculatedMassKg",
                          "Gap (kg)", "Gap (%)", "MassAdjustmentKg"]].round(1),
                 hide_index=True, use_container_width=True)
    if not len(c34):
        st.caption("Estimated mass appears after the first run (T41).")

    case = st.selectbox("Vehicle", cases["CaseKey"],
                        format_func=lambda k: f"{k} · {cases.set_index('CaseKey').loc[k, 'DsV']}")
    row = cases[cases["CaseKey"] == case].iloc[0]
    est = None
    if len(c34) and (c34["IDCase"] == row["IDCase"]).any():
        est = float(c34.loc[c34["IDCase"] == row["IDCase"], "CalculatedMassKg"].iloc[0])
    key = f"t38_{ida}_{case}"
    declared = st.number_input("Declared mass (kg)", min_value=0.0, step=1.0,
                               value=float(row["DeclaredMassKg"] or 0.0), key=key + "_d",
                               disabled=not ctx.can_edit)
    source = st.text_input("Source of the declared mass", value=row["DeclaredSource"] or "",
                           key=key + "_src", disabled=not ctx.can_edit)
    if declared and est is not None:
        st.info(f"Declared {declared:,.1f} kg · Estimated {est:,.1f} kg · "
                f"Gap {declared - est:+,.1f} kg")
    if st.button("Calibrate to declared mass", disabled=not ctx.can_edit or est is None
                 or not declared):
        st.session_state[key + "_adj"] = round(declared - est, 6)
    adj = st.number_input("Adjustment (kg, signed)", step=1.0, format="%.1f",
                          value=float(st.session_state.get(key + "_adj", row["MassAdjustmentKg"])),
                          key=key + "_adjin", disabled=not ctx.can_edit)
    mine = c34[c34["IDCase"] == row["IDCase"]] if len(c34) else c34
    est_s = ref_s = None
    if len(mine):
        est_s = None if pd.isna(mine["BodyShareEstimated"].iloc[0]) \
            else float(mine["BodyShareEstimated"].iloc[0])
        ref_s = None if pd.isna(mine["BodyShareReference"].iloc[0]) \
            else float(mine["BodyShareReference"].iloc[0])
    default_s = est_s
    own_s = st.checkbox("Set the Body share s myself", value=row["MassBodyShare"] is not None,
                        key=key + "_own", disabled=not ctx.can_edit)
    if own_s:
        s = st.slider("Body share s (Chassis gets 1 − s)", 0.0, 1.0,
                      float(row["MassBodyShare"] if row["MassBodyShare"] is not None
                            else (default_s if default_s is not None else 0.5)),
                      0.01, key=key + "_s", disabled=not ctx.can_edit)
    else:
        s = default_s
        st.caption(f"s = {default_s:.3f} (Body share of the estimated masses of this vehicle)"
                   if default_s is not None else
                   "s = Body share of the estimated masses of this vehicle (known after the "
                   "first run)")
    dev = b1_choices.share_deviation(est_s, ref_s)
    if dev is not None:
        msg = (f"Body share: estimated {est_s:.3f} · GREET reference {ref_s:.3f} "
               f"(recipe {row['IDVMR']}) · difference {100 * dev:+.1f} points. "
               "The reference does not enter the calculation.")
        if abs(dev) >= b1_choices.SHARE_DEVIATION_WARN:
            st.warning(msg + " The gap is large: consider reviewing the betas and the "
                       "reference masses (T13).")
        else:
            st.caption(msg)
    if adj and s is not None:
        st.table(pd.DataFrame({"Group": ["Body (A)", "Chassis (B)", "Total"],
                               "Calibration (kg)": [round(s * adj, 1), round((1 - s) * adj, 1),
                                                    round(adj, 1)]}))
    st.caption("Body and Chassis cannot become negative (I40); a violating adjustment stops "
               "the run with the minimum allowed value.")
    left, right = st.columns(2)
    if left.button("Save", disabled=not ctx.can_edit):
        conn.execute("UPDATE D07_AnalysisVehicle SET DeclaredMassKg = ?, MassAdjustmentKg = ?, "
                     "MassBodyShare = ?, DeclaredSource = ? WHERE IDA = ? AND IDCase = ?",
                     (declared or None, float(adj), s if own_s else None, source or None, ida,
                      int(row["IDCase"])))
        st.success("Saved. Freeze the analysis again (T41) to use it.")
    if right.button("Reset", disabled=not ctx.can_edit):
        conn.execute("UPDATE D07_AnalysisVehicle SET DeclaredMassKg = NULL, MassAdjustmentKg = 0, "
                     "MassBodyShare = NULL, DeclaredSource = NULL WHERE IDA = ? AND IDCase = ?",
                     (ida, int(row["IDCase"])))
        for suffix in ("_adj",):
            st.session_state.pop(key + suffix, None)
        st.rerun()

    if len(c34):
        st.download_button("Download CSV", c34.to_csv(index=False),
                           file_name=f"mass_validation_{last}.csv", mime="text/csv")
navigation.link("T04")
