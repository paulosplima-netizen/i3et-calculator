"""T16 · Maintenance — which parts are replaced during the vehicle life, and when.

The number of replacements is computed from the interval (km) and the life;
there is no replacement at the end of life. Choices are saved in D10 and are
frozen with the analysis (T41).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import b1_choices, maintenance
from ui import flow, navigation

ctx = flow.begin("Maintenance", edit=True)
with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    if ida is None:
        st.stop()
    items = pd.read_sql_query("SELECT * FROM P31_MaintenanceItem ORDER BY IDMI", conn)
    saved = b1_choices.load(conn, ida) or {
        "MaintenanceMode": "Sim", "Scenario": "REFERENCE", "VehicleLifeKm": None,
        "EoLMethod": b1_choices.DEFAULT_EOL, "items": []}

    st.markdown("**Reference** uses the intervals approved for the calculator; **User** lets you "
                "change the interval of each item (km) or switch it off.")
    mode = st.radio("Maintenance", list(maintenance.MODES),
                    index=list(maintenance.MODES).index(saved["MaintenanceMode"]),
                    horizontal=True, disabled=not ctx.can_edit,
                    help="Sim: parts and fluids. Sim Bat: also the traction battery. "
                         "Não: no replacements.")
    scenario = st.radio("Scenario", ["REFERENCE", "USER"],
                        index=["REFERENCE", "USER"].index(saved["Scenario"]), horizontal=True,
                        disabled=not ctx.can_edit)
    life = st.number_input("Vehicle life (km) — empty uses the panel value",
                           min_value=0.0, value=float(saved["VehicleLifeKm"] or 0.0),
                           step=10000.0, disabled=not ctx.can_edit)

    user = {i["IDMI"]: i for i in saved["items"]}
    table = items.copy()
    table["Reference km"] = table["IntervalKm"]
    table["IntervalKm"] = [user[i]["IntervalKm"] if i in user and user[i]["IntervalKm"]
                           is not None else k for i, k in zip(table["IDMI"], table["IntervalKm"])]
    table["Active"] = [user[i]["Active"] if i in user else True for i in table["IDMI"]]
    shown = [c for c in ("IDMI", "ItemKind", "Reference km", "IntervalKm", "Active")
             if c in table.columns]
    edited = st.data_editor(
        table[shown], hide_index=True, use_container_width=True,
        disabled=[c for c in shown if c not in ("IntervalKm", "Active")]
        if scenario == "USER" and ctx.can_edit else True,
        key=f"t16_items_{ida}")
    if scenario == "REFERENCE":
        st.caption("Reference scenario: the table is read-only.")

    if st.button("Save maintenance choices", disabled=not ctx.can_edit):
        rows = [{"IDMI": r.IDMI,
                 "IntervalKm": None if pd.isna(r.IntervalKm) else float(r.IntervalKm),
                 "Active": bool(r.Active)} for r in edited.itertuples()]
        try:
            b1_choices.save_maintenance(conn, ida, mode=mode, scenario=scenario,
                                        vehicle_life_km=float(life) or None, items=rows,
                                        author=ctx.ident.get("ProjectName", ""))
            st.success("Saved. Freeze the analysis again (T41) to use these choices.")
        except ValueError as e:
            st.error(str(e))

navigation.link("T18")
