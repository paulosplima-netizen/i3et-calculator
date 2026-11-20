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
from core import formatting as fm
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
        "a.MassBodyShare, a.DeclaredSource, a.SizingOrigin, a.MassCalibrationMode, a.IDV, "
        "d.IDVMR FROM D07_AnalysisVehicle a "
        "JOIN D01_Vehicle v ON v.IDV = a.IDV JOIN D02_EvaluationAlternative d "
        "ON d.IDV = a.IDV AND d.IDEA = a.IDEA WHERE a.IDA = ? ORDER BY a.IDCase", conn,
        params=(ida,))
    if cases.empty:
        st.info("This analysis has no vehicles yet.")
        st.stop()
    p25 = {int(r[0]): [{"IDVP": 25, "GC": r[1], "IsCalculated": r[2]}] for r in conn.execute(
        "SELECT IDV, GC, IsCalculated FROM D03_VehicleParamValue WHERE IDVP = 25")}
    basis = {int(r["IDCase"]): b1_choices.mass_basis(r.to_dict(), p25.get(int(r["IDV"])))
             for _, r in cases.iterrows()}
    cases["Mass basis"] = cases["IDCase"].map(lambda i: basis[int(i)]["basis"])
    cases["Declared in use (kg)"] = cases["IDCase"].map(lambda i: basis[int(i)]["declared_kg"])
    cases["Auto"] = cases["IDCase"].map(lambda i: "yes" if basis[int(i)]["auto"] else "no")
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
    summary["Gap (kg)"] = summary["Declared in use (kg)"] - summary["CalculatedMassKg"]
    summary["Gap (%)"] = 100 * summary["Gap (kg)"] / summary["CalculatedMassKg"]
    fmt_ = flow.display_format(conn)
    shown = fm.frame(summary[["CaseKey", "CaseRole", "DsV", "Mass basis", "Declared in use (kg)",
                              "CalculatedMassKg", "Gap (kg)", "Gap (%)", "Auto",
                              "MassAdjustmentKg"]],
                     {"Declared in use (kg)": "mass", "CalculatedMassKg": "mass",
                      "Gap (kg)": "mass",
                      "MassAdjustmentKg": "mass", "Gap (%)": "generic"}, fmt_)
    st.dataframe(shown, hide_index=True, use_container_width=True)
    if not len(c34):
        st.caption("Estimated mass appears after the first run (T41).")

    case = st.selectbox("Vehicle", cases["CaseKey"],
                        format_func=lambda k: f"{k} · {cases.set_index('CaseKey').loc[k, 'DsV']}")
    row = cases[cases["CaseKey"] == case].iloc[0]
    est = None
    if len(c34) and (c34["IDCase"] == row["IDCase"]).any():
        est = float(c34.loc[c34["IDCase"] == row["IDCase"], "CalculatedMassKg"].iloc[0])
    key = f"t38_{ida}_{case}"
    mb = basis[int(row["IDCase"])]
    if mb["basis"] == b1_choices.BASIS_ITERATIVE:
        st.info("Theoretical vehicle: parameter 25 is calculated (there is no known mass), so "
                "nothing is allocated and the estimated mass is the result. Type a declared "
                "mass below only if you have one.")
    elif mb["basis"] == b1_choices.BASIS_MARKET:
        st.info(f"Market vehicle: the declared mass is parameter 25 "
                f"({mb['declared_kg']:.1f} kg). Type a value below only to override it.")
    declared = st.number_input("Declared mass (kg)", min_value=0.0, step=1.0,
                               value=float(row["DeclaredMassKg"] or 0.0), key=key + "_d",
                               disabled=not ctx.can_edit)
    source = st.text_input("Source of the declared mass", value=row["DeclaredSource"] or "",
                           key=key + "_src", disabled=not ctx.can_edit)
    if not declared and mb["declared_kg"]:
        declared = mb["declared_kg"]
    if declared and est is not None:
        fmt_ = flow.display_format(conn)
        st.info(f"Declared {fm.fmt(declared, 'mass', fmt_, with_unit=True)} · Estimated "
                f"{fm.fmt(est, 'mass', fmt_, with_unit=True)} · Gap "
                f"{'+' if declared >= est else '-'}"
                f"{fm.fmt(abs(declared - est), 'mass', fmt_, with_unit=True)}")
    auto = st.checkbox(
        "Calibrate automatically to the declared mass (the gap goes to Body and Chassis)",
        value=mb["auto"], key=key + "_auto",
        disabled=not ctx.can_edit or not declared,
        help="On by default for market vehicles with a known mass; off for theoretical "
             "vehicles and for the workbook's reference configurations (to keep parity).")
    if st.button("Fix the gap of the last run as a manual adjustment",
                 disabled=not ctx.can_edit or est is None or not declared):
        st.session_state[key + "_adj"] = round(declared - est, 6)
    adj = st.number_input("Manual adjustment (kg, signed; overrides the automatic one)",
                          step=1.0, format="%.1f",
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
        fmt_ = flow.display_format(conn)
        calib = pd.DataFrame({"Group": ["Body (A)", "Chassis (B)", "Total"],
                              "Calibration": [s * adj, (1 - s) * adj, adj]})
        st.table(fm.frame(calib, {"Calibration": "mass"}, fmt_, rename=True))
    st.caption("Body and Chassis cannot become negative (I40); a violating adjustment stops "
               "the run with the minimum allowed value.")
    left, right = st.columns(2)
    if left.button("Save", disabled=not ctx.can_edit):
        conn.execute("UPDATE D07_AnalysisVehicle SET DeclaredMassKg = ?, MassAdjustmentKg = ?, "
                     "MassBodyShare = ?, DeclaredSource = ? WHERE IDA = ? AND IDCase = ?",
                     (None if declared == mb["declared_kg"] and mb["basis"]
                      == b1_choices.BASIS_MARKET else (declared or None), float(adj),
                      s if own_s else None, source or None, ida, int(row["IDCase"])))
        default_auto = bool(declared) and row["SizingOrigin"] == "Manufacturer"
        mode = "ON" if auto and not default_auto else "OFF" if not auto and default_auto \
            else None
        conn.execute("UPDATE D07_AnalysisVehicle SET MassCalibrationMode = ? WHERE IDA = ? "
                     "AND IDCase = ?", (mode, ida, int(row["IDCase"])))
        st.success("Saved. Freeze the analysis again (T41) to use it.")
    if right.button("Reset", disabled=not ctx.can_edit):
        conn.execute("UPDATE D07_AnalysisVehicle SET DeclaredMassKg = NULL, MassAdjustmentKg = 0, "
                     "MassBodyShare = NULL, DeclaredSource = NULL, MassCalibrationMode = NULL "
                     "WHERE IDA = ? AND IDCase = ?",
                     (ida, int(row["IDCase"])))
        for suffix in ("_adj",):
            st.session_state.pop(key + suffix, None)
        st.rerun()

    if len(c34):
        st.download_button("Download CSV", c34.to_csv(index=False),
                           file_name=f"mass_validation_{last}.csv", mime="text/csv")
navigation.link("T04")
