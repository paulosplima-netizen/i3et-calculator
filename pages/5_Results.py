"""Screen 5 — mass and emissions, group by group and material by material."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import charts
from ui import components

atual = components.page("Results", "§8 to §14")
base, resultados, log = atual

d01 = base["D01"]
nomes = dict(zip(d01["DsV"], d01["IDV"]))
escolhido = st.selectbox("Vehicle", options=list(nomes))
idv = int(nomes[escolhido])
resultado = resultados.get((idv, 1))
if resultado is None:
    st.warning("This vehicle has no scenario yet. Set one on **Scenario**.")
    st.stop()

t = resultado["totals"]
# A unidade vai no rotulo e o numero fica com uma casa: numa caixa estreita,
# o valor inteiro cabe e nao e cortado no meio. A precisao completa esta nas
# tabelas logo abaixo e em toda exportacao.
col1, col2, col3, col4 = st.columns(4)
col1.metric("Vehicle mass (kg)", components.number(t["MassIDV"], 1))
col2.metric("Materials (kg CO₂e)", components.number(t["GHGMaterials"], 1))
col3.metric("Assembly (kg CO₂e)", components.number(t["GHGAssembly"], 1))
col4.metric("Cradle to gate (kg CO₂e)",
            components.number(t["GHGCradleToGate"], 1),
            help=("Assembly is included when the boundary is MAT_ASM. "
                  f"Boundary in use: {t['Boundary']}."))
components.coverage_note(t)

st.divider()
st.subheader("Where the total comes from")
c10 = resultado["C10"].sort_values("GHGIDGG", ascending=False)
passos = [(str(r.IDGG), float(r.GHGIDGG)) for r in c10.itertuples()
          if float(r.GHGIDGG) > 0]
if t["Boundary"] == "MAT_ASM" and t["GHGAssembly"]:
    passos.append(("Assembly", float(t["GHGAssembly"])))
components.chart(charts.waterfall(
    passos, total_rotulo="Total", unidade="kg CO₂e",
    titulo=f"{escolhido}: contribution of each GREET group"))

components.how_was_this_calculated(
    "Emissions of one group",
    "GHG_group = Σ_materials  Mass_group × MshareGG × EF_material",
    {"Mass_group": "mass of the group (C02)",
     "MshareGG": "share of the material in the group (P16, by recipe)",
     "EF_material": "emission factor of the material (P11, by version)"},
    "§12")

aba1, aba2, aba3, aba4 = st.tabs(
    ["By GREET group", "By material", "Battery", "Assembly"])

with aba1:
    components.table(resultado["C10"])
    st.caption("Mass and emissions of every group, including the ones that "
               "weigh nothing in this vehicle.")

with aba2:
    c11 = resultado["C11"].sort_values("GHGIDM", ascending=False)
    components.table(c11)
    detalhe = st.checkbox("Show the material × group detail, with shares and factors")
    if detalhe:
        components.table(resultado["C03"])

with aba3:
    c07 = resultado["C07"]
    if not len(c07):
        st.info("This vehicle has no traction battery.")
    else:
        components.table(c07)
        modelo = str(c07.iloc[0]["IDBMd"])
        p19 = base["P19"]
        linha = p19[p19["IDBMd"] == modelo]
        if len(linha):
            metodo = linha.iloc[0]["GHGMethod"]
            st.caption(f"Model `{modelo}`, priced by **{metodo}**. "
                       + ("A carbon intensity per kilogram."
                          if metodo == "gravimetric"
                          else "A material composition, material by material."))
        else:
            st.warning(f"Model `{modelo}` is not described in P19: its mass is "
                       "counted and its factor is declared absent.")

with aba4:
    components.table(resultado["C13"])
    metodo = base["P23"]
    cen = base["D02"]
    idapv = cen[cen["IDV"] == idv].iloc[0]["IDAPV"]
    linha = metodo[metodo["IDAPV"] == idapv]
    if len(linha):
        st.caption(f"`{idapv}` — method **{linha.iloc[0]['Method']}**. "
                   f"{linha.iloc[0]['DsAPV']}")

st.divider()
st.subheader("Every vehicle, side by side")
r10 = pd.DataFrame([{
    "Vehicle": d01[d01["IDV"] == v].iloc[0]["DsV"],
    "Powertrain": d01[d01["IDV"] == v].iloc[0]["IDVPT"],
    "Mass (kg)": r["totals"]["MassIDV"],
    "Cradle to gate (kg CO₂e)": r["totals"]["GHGCradleToGate"],
    "kg CO₂e / kg": r["totals"]["GHGperKg"],
    "Mass without factor (kg)": r["totals"]["MassNoFactor"],
} for (v, _e), r in sorted(resultados.items())])
components.chart(charts.bar_chart(
    [(f"{r.Vehicle} ({r.Powertrain})", float(r._4)) for r in r10.itertuples()],
    unidade="kg CO₂e per vehicle", titulo="Cradle to gate, every vehicle"))
components.table(r10)
