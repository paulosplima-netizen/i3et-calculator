"""T17 · End of life — how disposal and recycling are counted.

Three methods: glider and battery with the panel factors (default), the aggregate
vehicle factor of the BR23 list (as the i3ET does today), or excluded.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import b1_choices, endoflife
from core import formatting as fm
from ui import flow, navigation

LABELS = {"GLIDER_BATTERY": "Glider and battery (panel factors X76 and X77)",
          "AGGREGATE_VEHICLE": "Aggregate vehicle factor (list IDM 100, as in the i3ET)",
          "EXCLUDED": "Excluded"}

ctx = flow.begin("End of life", edit=True)
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    if ida is None:
        st.stop()
    current = conn.execute("SELECT EoLMethod FROM D06_Analysis WHERE IDA = ?",
                           (ida,)).fetchone()[0]
    method = st.radio("Method", list(endoflife.METHODS), format_func=LABELS.get,
                      index=list(endoflife.METHODS).index(current),
                      disabled=not ctx.can_edit)
    if st.button("Save end-of-life method", disabled=not ctx.can_edit):
        b1_choices.save_eol(conn, ida, method)
        st.success("Saved. Freeze the analysis again (T41) to use it.")
    rs = flow.runs(conn, ida)
    if rs:
        last = rs[-1]["RunID"]
        eol = pd.read_sql_query(
            "SELECT a.CaseKey, c.EoLMethod, c.GliderMassKg, c.BatteryKWh, c.FactorGlider, "
            "c.FactorBattery, c.FactorVehicle, c.GHGEoL FROM C16_EndOfLife c JOIN "
            "D07_AnalysisVehicle a ON a.IDA = c.IDA AND a.IDCase = c.IDCase "
            "WHERE c.RunID = ?", conn, params=(last,))
        st.subheader(f"Last run ({last})")
        st.dataframe(fm.frame(eol, {"GliderMassKg": "mass", "FactorGlider": "factor",
                                    "FactorBattery": "factor", "FactorVehicle": "factor",
                                    "GHGEoL": "ghg"}, flow.display_format(conn)),
                     hide_index=True, use_container_width=True)

navigation.link("T18")
