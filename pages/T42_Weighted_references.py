"""T42 · Concept vehicles and weighted references (master only).

For each category (A0 to A5) shows the segments that make up the reference vehicle, the
vehicles in them with their licensed units and weights, the weighted parameters recomputed
from the units (C33) against the values stored in the base (from the Excel model), and the
coverage of the segments against the ANFAVEA total. Read-only.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import market_data as md
from ui import flow, master

flow.begin("Concept vehicles and weighted references", needs_project=False)
master.require_master("Weighted references")

st.caption("Sources: licensed units from FENABRAVE; fleet total from ANFAVEA; vehicle "
           "parameters from the Excel model. The weighting is exclusive to the master user.")
with master.reference_conn() as conn:
    cats = pd.read_sql_query("SELECT IDVC, DsVC, IDMVSelecao, IDMVRepresentative FROM "
                             "P29_VehicleCategory ORDER BY CaseDigit", conn)
    total = conn.execute("SELECT Units, SourceFL FROM P60_FleetLicensingTotal "
                         "WHERE RefYear = 2025").fetchone()
    cob = md.segment_coverage(conn, total[0]) if total else None
    if cob:
        c1, c2, c3 = st.columns(3)
        c1.metric("Units in the segments", f"{cob['units']:,}")
        c2.metric("Fleet total, 2025 (ANFAVEA)", f"{cob['total']:,}")
        c3.metric("Coverage", f"{cob['share'] * 100:.1f}%")
        st.caption("Licensing (ANFAVEA) and registration by model (FENABRAVE) are defined "
                   "differently; read the coverage as an indicator, not an identity.")
    escolha = st.selectbox("Category", [f"{r.IDVC} · {r.DsVC}" for r in cats.itertuples()])
    idvc = escolha.split(" · ")[0]
    seg = pd.read_sql_query("SELECT IDVDT AS Design, IDVS AS Size, FuelGroup AS 'Fuel group', "
                            "IDVPT AS Powertrain, SheetRow AS 'Workbook row' FROM "
                            "P70_ReferenceSegment WHERE IDVC = ?", conn, params=(idvc,))
    st.subheader("Segments")
    st.dataframe(seg, hide_index=True, use_container_width=True)
    ref = md.reference_params(conn, idvc)
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
