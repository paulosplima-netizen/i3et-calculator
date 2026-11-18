"""T04 · Selected Parameters — P30 in three depths, with D08 (docs/06, T04)."""

from __future__ import annotations

import streamlit as st

from core import control_params as cp
from ui import flow, navigation

ctx = flow.begin("Selected Parameters", edit=True)
LEVELS = {"Basic": ("B",), "Expert": ("B", "E"), "Expanded": ("B", "E", "X")}
#: Parametros do painel que a T03 define (modo, combustivel, norma, curva, lista de fatores).
CONFIG_LINKED = {"Fuel considered in Graphs", "Test Cycle", "Daily Distance CDF",
                 "Emission Factors List"}


def _inconsistent(lo, mf, hi) -> bool:
    """Faixa de referencia incoerente: minimo acima do maximo, ou tipico fora dela."""
    if lo is None or hi is None:
        return False
    a, b = min(lo, hi), max(lo, hi)
    return lo > hi or (mf is not None and not a <= mf <= b)


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
        "MaxValue, Reference, UsedByModule, Cell FROM P30_ControlParam "
        "ORDER BY Section, Cell").fetchall()

    t1, t2, t3 = st.columns([3, 1.5, 2])
    term = t1.text_input("Search parameter", placeholder="id, name or unit").strip().lower()
    only_changed = t2.checkbox("Changed only")
    n_over = sum(1 for e in eff.values() if e.source == "User")
    if t3.button("Restore this depth", disabled=not (ctx.can_edit and n_over)):
        cp.restore_profile(conn, ida, profile)
        st.rerun()

    def _shown(r):
        idcp, _, lvl, ds, ut = r[0], r[1], r[2], r[3], r[4]
        if lvl not in LEVELS[profile]:
            return False
        if only_changed and eff[idcp].source != "User":
            return False
        return term in " ".join([idcp, ds or "", ut or ""]).lower()

    visible = [r for r in rows if _shown(r)]
    st.caption(f"{len(visible)} shown · {n_over} overrides · "
               "parameters set in Project Configuration are read-only here")
    for section in sorted({r[1] for r in visible}):
        subset = [r for r in visible if r[1] == section]
        with st.expander(f"{section} · {len(subset)}", expanded=True):
            for idcp, sec, lvl, ds, ut, calc, lo, mf, hi, ref, mod, cell in subset:
                e = eff[idcp]
                a, b, c, d = st.columns([3, 1.4, 2.4, 1])
                a.write(f"**{ds}**  \n`{idcp}` · {ut or '—'} · module {mod or '—'}")
                if calc or ds.strip() in CONFIG_LINKED:
                    b.write(e.value if e.value is not None else e.text)
                    if calc:
                        c.caption("Calculated")
                    else:
                        with c:
                            navigation.link("T03", "Set in Project Configuration")
                    continue
                if e.text is not None and e.value is None:
                    new = b.text_input("Value", e.text, key=f"v{idcp}",
                                       label_visibility="collapsed", disabled=not ctx.can_edit)
                    val, txt = None, new
                else:
                    new = b.number_input("Value", value=float(e.value or 0.0), key=f"v{idcp}",
                                         label_visibility="collapsed",
                                         disabled=not ctx.can_edit, format="%g")
                    val, txt = new, None
                c.caption(f"range {lo if lo is not None else '—'} · typical "
                          f"{mf if mf is not None else '—'} · {hi if hi is not None else '—'} · "
                          f"{'edited' if e.source == 'User' else 'default'} · "
                          f"source {' · '.join(x for x in (cell, ref) if x) or '—'}")
                if e.out_of_range:
                    c.warning("outside the usual range")
                if _inconsistent(lo, mf, hi):
                    c.warning("inconsistent reference range")
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
