"""T04 · Selected Parameters — P30 in three depths, with D08 (docs/06, T04)."""

from __future__ import annotations

import streamlit as st

from core import control_params as cp
from ui import flow

ctx = flow.begin("Selected Parameters", edit=True)
LEVELS = {"Basic": ("B",), "Expert": ("B", "E"), "Expanded": ("B", "E", "X")}

with flow.connect(ctx.path) as conn:
    ida = flow.pick_analysis(conn)
    if ida is None:
        st.stop()
    if flow.selected_count() > 1:
        st.warning("Blocked: more than one project is selected.")
        st.stop()
    profile = st.radio("Depth", list(LEVELS), horizontal=True,
                       index=list(LEVELS).index(
                           conn.execute("SELECT ParamProfile FROM D06_Analysis WHERE IDA=?",
                                        (ida,)).fetchone()[0]))
    eff = cp.effective_values(conn, ida, profile)
    rows = conn.execute(
        "SELECT IDCP, Section, Level, DsCP, utCP, IsCalculated, MinValue, MostFrequent, "
        "MaxValue, Reference, UsedByModule FROM P30_ControlParam ORDER BY Section, Cell").fetchall()
    sections = sorted({r[1] for r in rows})
    section = st.selectbox("Section", sections)
    for idcp, sec, lvl, ds, ut, calc, lo, mf, hi, ref, mod in rows:
        if sec != section or lvl not in LEVELS[profile]:
            continue
        e = eff[idcp]
        a, b, c, d = st.columns([3, 1.4, 2, 1])
        a.write(f"**{ds}**  \n`{idcp}` · {ut or '—'} · module {mod or '—'}")
        if calc:
            b.write(e.value if e.value is not None else e.text)
            c.caption("Calculated")
            continue
        if e.text is not None and e.value is None:
            new = b.text_input("Value", e.text, key=f"v{idcp}", label_visibility="collapsed",
                               disabled=not ctx.can_edit)
            val, txt = None, new
        else:
            new = b.number_input("Value", value=float(e.value or 0.0), key=f"v{idcp}",
                                 label_visibility="collapsed", disabled=not ctx.can_edit,
                                 format="%g")
            val, txt = new, None
        c.caption(f"range {lo if lo is not None else '—'} · typical "
                  f"{mf if mf is not None else '—'} · {hi if hi is not None else '—'} · "
                  f"{'edited' if e.source == 'User' else 'default'}")
        if e.out_of_range:
            c.warning("outside the range")
        if ctx.can_edit:
            changed = (val is not None and e.value is not None and val != e.value) or \
                      (txt is not None and txt != e.text)
            if changed and d.button("Save", key=f"s{idcp}"):
                cp.set_value(conn, ida, idcp, profile, value=val, text=txt,
                             source=ref or "User, T04")
                st.rerun()
            if e.source == "User" and d.button("Restore", key=f"r{idcp}"):
                cp.restore(conn, ida, idcp, profile)
                st.rerun()
