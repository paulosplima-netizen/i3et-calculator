"""T47 · Display format — decimals, units, separators and notation.

Only the display changes: calculations and frozen results keep full precision, and the
CSV is rounded only if you ask for it. The setting lives in the project file (D22), so
a report can say which format it used. New screen: it has no revised prototype yet.
"""

from __future__ import annotations

import streamlit as st

from core import formatting as fm
from ui import flow

ctx = flow.begin("Display format", edit=True)
with flow.connect(ctx.path) as conn:
    current, stored = fm.load(conn)
    st.caption("Only the display changes. Calculations and frozen results are never "
               "rounded; the CSV export rounds only if you tick the box below.")
    names = {"default": "Default (screens, 1 decimal)", "article": "Article (rounded)",
             "audit": "Audit (full precision)", "custom": "Custom"}
    chosen = st.radio("Profile", list(names), format_func=names.get,
                      index=list(names).index(current.profile), horizontal=True)
    base = current if chosen == current.profile else fm.profile(chosen)
    editable = chosen == "custom"
    if not editable:
        st.caption("Choose Custom to change the individual settings.")

    st.subheader("Decimals by quantity")
    cols = st.columns(5)
    decimals = {}
    for i, (key, (label, _)) in enumerate(fm.CLASSES.items()):
        value = base.decimals.get(key)
        decimals[key] = cols[i % 5].number_input(
            label, min_value=0, max_value=12, value=2 if value is None else int(value),
            step=1, disabled=not editable, key=f"dec_{key}")
    if base.profile == "audit":
        decimals = {k: None for k in fm.CLASSES}

    st.subheader("Units and notation")
    c1, c2, c3, c4 = st.columns(4)
    mass_unit = c1.selectbox("Mass", ["kg", "t"], index=["kg", "t"].index(base.mass_unit),
                             disabled=not editable)
    ghg_unit = c2.selectbox("GHG emissions", ["kg", "t"], index=["kg", "t"].index(base.ghg_unit),
                            disabled=not editable)
    share_as = c3.selectbox("Shares", ["percent", "fraction"],
                            index=["percent", "fraction"].index(base.share_as),
                            disabled=not editable)
    sci = c4.number_input("Scientific notation below (0 = never)", min_value=0.0,
                          value=float(base.sci_below), format="%.6f", disabled=not editable)

    st.subheader("Separators")
    s1, s2, s3 = st.columns(3)
    dec_sep = s1.selectbox("Decimal", [".", ","], index=[".", ","].index(base.decimal_sep),
                           disabled=not editable)
    thou = s2.selectbox("Thousands", [",", ".", " ", ""],
                        index=[",", ".", " ", ""].index(base.thousands_sep),
                        format_func=lambda x: {" ": "space", "": "none"}.get(x, x),
                        disabled=not editable)
    csv_sep = s3.selectbox("CSV field separator", [",", ";"],
                           index=[",", ";"].index(base.csv_sep), disabled=not editable,
                           help="Use ; with a decimal comma to open the CSV in Brazilian Excel.")
    csv_rounded = st.checkbox("Round the numbers in the CSV export too", value=base.csv_rounded,
                              disabled=not editable)

    try:
        new = fm.validate(fm.Format(
            profile=chosen, decimals=decimals, mass_unit=mass_unit, ghg_unit=ghg_unit,
            share_as=share_as, decimal_sep=dec_sep, thousands_sep=thou, csv_sep=csv_sep,
            sci_below=float(sci), csv_rounded=csv_rounded))
    except ValueError as e:
        st.error(str(e))
        new = None

    if new is not None:
        st.subheader("Preview")
        sample = [("Mass", 1234.5678, "mass"), ("GHG emissions", 8765.4321, "ghg"),
                  ("Share", 0.123456, "share"), ("Emission factor", 0.00123456, "factor"),
                  ("Ratio", 0.684813703, "ratio"), ("Distance", 200000, "distance")]
        rows = [{"Quantity": n, "Stored value": v, "Shown as": fm.fmt(v, k, new, with_unit=True)}
                for n, v, k in sample]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        st.caption(fm.describe(new))
        if ctx.can_edit and st.button("Save format"):
            fm.save(conn, new)
            st.success("Saved. Screens and exports of this project use it from now on.")
    if stored:
        st.caption("This project has a saved format.")
