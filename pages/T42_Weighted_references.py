"""T42 · Concept vehicles and weighted references (master only).

For each category (A0 to A5) shows the segments that make up the reference vehicle, the
vehicles in them with their licensed units and weights, the weighted parameters recomputed
from the units (C33) against the values stored in the base (from the Excel model), and the
coverage of the segments against the FENABRAVE market total, the design × powertrain
split of the licensed units and an Excel export comparing the Excel model with the app's
recalculation. The master can edit the segments of a category (the default is the Excel
model's definition and can be restored), compute the reference of another powertrain and see
which market vehicles come closest to the weighted reference.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import market_data as md
from ui import flow, master

flow.begin("Concept vehicles and weighted references", needs_project=False)
master.require_master("Weighted references")

st.caption("Sources: licensed units and market total from FENABRAVE; vehicle "
           "parameters from the Excel model. The weighting is exclusive to the master user.")
with master.reference_conn() as conn:
    cats = pd.read_sql_query("SELECT IDVC, DsVC, IDMVSelecao, IDMVRepresentative FROM "
                             "P29_VehicleCategory ORDER BY CaseDigit", conn)
    def _p60(fonte, classe):
        r = conn.execute("SELECT Units FROM P60_FleetLicensingTotal WHERE SourceName = ? AND "
                         "RefYear = 2025 AND VehicleClass = ? AND IsAdopted = 1",
                         (fonte, classe)).fetchone()
        return r[0] if r else None
    total = _p60("FENABRAVE", "LightVehicles")
    ranking = conn.execute("SELECT COALESCE(SUM(UnitsAdopted),0) FROM P47_MarketSales s "
                           "JOIN P48_MarketSalesEdition e USING (IDMSE) "
                           "WHERE e.IsAdopted = 1").fetchone()[0]
    anf = [_p60("ANFAVEA", c) for c in ("Automobiles", "LightCommercials")]
    cob = md.segment_coverage(conn, total) if total else None
    if cob:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Six reference segments", f"{cob['units']:,}")
        c2.metric("Top 50 + top 50 (FENABRAVE)", f"{ranking:,}",
                  f"{ranking / total * 100:.1f}% of market")
        c3.metric("Market total, 2025 (FENABRAVE)", f"{total:,}")
        c4.metric("Segments / market", f"{cob['share'] * 100:.1f}%")
        if None not in anf:
            st.caption(f"ANFAVEA yearbook 2026 (tables 2.2.1): {sum(anf):,} light vehicles in "
                       f"2025, {sum(anf) - total:+,} against the FENABRAVE total. The model "
                       "uses FENABRAVE throughout; ANFAVEA is kept for the fleet module.")
        st.caption("The top-50 lists include vans and chassis; only hatch, sedan, SUV and "
                   "pickup segments enter the reference vehicles.")
    ed = conn.execute("SELECT IDMSE FROM P48_MarketSalesEdition WHERE IsAdopted = 1").fetchone()
    if ed:
        piv = md.design_powertrain_pivot(conn, ed[0])
        grupos = sorted({g for g, _ in piv}, key=lambda g: (g == "Other", g))
        pts = sorted({p for _, p in piv})
        quadro = pd.DataFrame([{"Group": g, **{p: piv.get((g, p)) for p in pts},
                                "Total": sum(piv.get((g, p), 0) for p in pts)}
                               for g in grupos])
        st.subheader("Licensed units by design group and powertrain")
        st.dataframe(quadro, hide_index=True, use_container_width=True)
        st.caption(f"Edition {ed[0]}; grand total {sum(piv.values()):,}. Each row of the "
                   "source is one model and powertrain (never grouped).")
    import io
    buf = io.BytesIO()
    md.export_reference_xlsx(conn, buf)
    st.download_button("Export comparison to Excel (Excel model × recalculation)",
                       buf.getvalue(), file_name="reference_vehicles_comparison.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    escolha = st.selectbox("Category", [f"{r.IDVC} · {r.DsVC}" for r in cats.itertuples()])
    idvc = escolha.split(" · ")[0]
    seg = pd.read_sql_query("SELECT IDVDT AS Design, IDVS AS Size, FuelGroup AS 'Fuel group', "
                            "IDVPT AS Powertrain, SheetRow AS 'Workbook row' FROM "
                            "P70_ReferenceSegment WHERE IDVC = ?", conn, params=(idvc,))
    st.subheader("Segments")
    origem = conn.execute("SELECT COUNT(*) FROM P70_ReferenceSegment WHERE IDVC = ? AND "
                          "Origin = 'Master'", (idvc,)).fetchone()[0]
    st.caption("Definition edited by the master." if origem else
               "Default: the definition of the Excel model.")
    ed_seg = st.data_editor(
        seg[["Design", "Size", "Fuel group", "Powertrain"]], num_rows="dynamic",
        hide_index=True, use_container_width=True, key=f"seg_{idvc}",
        column_config={"Fuel group": st.column_config.SelectboxColumn(
            options=["EG", "D", "X"], help="EG = flex and gasoline; D = diesel; X = others")})
    b1, b2 = st.columns(2)
    if b1.button("Save segments (master)"):
        linhas = [{"IDVDT": r["Design"], "IDVS": r["Size"], "FuelGroup": r["Fuel group"],
                   "IDVPT": r["Powertrain"] or "ICEV"} for _, r in ed_seg.dropna(
                       subset=["Design", "Size", "Fuel group"]).iterrows()]
        try:
            n = md.save_segments(conn, idvc, linhas)
            st.success(f"{n} segments saved; the weighted parameters below use them.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    if b2.button("Restore the Excel model's segments"):
        md.restore_workbook_segments(conn, idvc)
        st.rerun()
    pts = [r[0] for r in conn.execute("SELECT DISTINCT IDVPT FROM P26_MarketVehicle "
                                      "WHERE IsSelecao = 0 ORDER BY IDVPT")]
    pt = st.selectbox("Powertrain of the reference", pts,
                      index=pts.index("ICEV") if "ICEV" in pts else 0,
                      help="The Excel model computes only the ICEV reference; the other "
                           "powertrains are derived by equivalence.")
    ref = md.reference_params(conn, idvc, powertrain=None if pt == "ICEV" else pt)
    prox = md.closest_vehicles(conn, idvc, pt)
    if prox:
        st.subheader("Market vehicles closest to the weighted reference")
        st.dataframe(pd.DataFrame(prox).drop(columns=["IDMV"]), hide_index=True,
                     use_container_width=True,
                     column_config={"Distance": st.column_config.NumberColumn(format="%.3f")})
        st.caption("Illustration only: the adopted parameters are the weighted ones. "
                   "Distance = root mean square of the relative deviations.")
    idsel = int(cats.loc[cats["IDVC"] == idvc, "IDMVSelecao"].iloc[0])
    stored = dict(conn.execute("SELECT IDMP, Value FROM P27_MarketVehicleParam "
                               "WHERE IDMV = ? AND ValueClass = 'Avg'", (idsel,)))
    nomes = dict(conn.execute("SELECT IDMP, DsMP FROM P54_MarketParam"))
    tabela = pd.DataFrame([{"Parameter": nomes.get(p, p), "Recomputed (C33)": v,
                            "Excel model": stored.get(p),
                            "Difference": v - stored[p] if p in stored else None}
                           for p, v in sorted(ref.items())])
    st.subheader("Weighted parameters")
    st.dataframe(tabela, hide_index=True, use_container_width=True)
    segs = conn.execute("SELECT IDVDT, IDVS, FuelGroup, IDVPT FROM P70_ReferenceSegment "
                        "WHERE IDVC = ?", (idvc,)).fetchall()
    veic = pd.read_sql_query("SELECT IDMV, Brand, Model, IDVDT, IDVS, Fuel, IDVPT, "
                             "COALESCE(SalesUnits, 0) AS Units FROM P26_MarketVehicle "
                             "WHERE IsSelecao = 0", conn)
    sel = veic[[any(md.norm(r.IDVDT) == md.norm(d) and md.norm(r.IDVS) == md.norm(s)
                    and md.fuel_group(r.Fuel) == g and r.IDVPT == p for d, s, g, p in segs)
                for r in veic.itertuples()]].copy()
    soma = sel["Units"].sum()
    sel["Weight"] = sel["Units"] / soma if soma else 0.0
    sel = sel.sort_values("Units", ascending=False).drop(columns=["IDMV"])
    st.subheader("Vehicles in the segments")
    st.dataframe(sel, hide_index=True, use_container_width=True,
                 column_config={"Weight": st.column_config.NumberColumn(format="%.3f")})
