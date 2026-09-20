"""Screen 3 — the values each vehicle is described by."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import params as P
from ui import components, state

atual = components.page("Vehicle parameters", "§7.2")
base, resultados, log = atual

d01 = base["D01"]
nomes = dict(zip(d01["DsV"], d01["IDV"]))
escolhido = st.selectbox("Vehicle", options=list(nomes))
idv = int(nomes[escolhido])
veiculo = d01[d01["IDV"] == idv].iloc[0]
proprio = bool(veiculo["IsUserDefined"])

st.write(
    "Exogenous values describe the vehicle and are yours to set. Endogenous "
    "ones are computed from them — shown here in grey, with the equation "
    "beside each. A value you supply is never undone by the equation that "
    "would have produced it; the `IsCalculated` column records which is which.")

if not proprio:
    st.info("This is a reference vehicle: its parameters are read-only. Create "
            "a copy on the **Vehicles** screen to change anything.")

p07 = base["P07"].set_index("IDVP")
d03 = base["D03"]
linhas = d03[d03["IDV"] == idv].copy()
calculado = {int(k): v for k, v in
             (resultados.get((idv, 1), {}).get("gc") or {}).items()}

tabela = []
for _, r in linhas.iterrows():
    idvp = int(r["IDVP"])
    p = p07.loc[idvp] if idvp in p07.index else None
    endogeno = idvp in set(P.ENDOGENOUS)
    tabela.append({
        "IDVP": idvp,
        "Parameter": p["DsVP"] if p is not None else "",
        "Unit": p["utVP"] if p is not None else "",
        "Class": "endogenous" if endogeno else "exogenous",
        "Stored": r["GC"],
        "Computed": calculado.get(idvp),
        "Text": r["GCText"],
        "IsCalculated": int(r["IsCalculated"] or 0),
        "Equation": (p["GCEquation"] if p is not None else None) or "",
    })
tabela = pd.DataFrame(tabela)

exo = tabela[tabela["Class"] == "exogenous"]
endo = tabela[tabela["Class"] == "endogenous"]

st.subheader("Exogenous — what you set")
if proprio:
    editado = st.data_editor(
        exo[["IDVP", "Parameter", "Unit", "Stored", "Text"]],
        hide_index=True, use_container_width=True, key=f"exo_{idv}",
        disabled=["IDVP", "Parameter", "Unit"],
        column_config={"Stored": st.column_config.NumberColumn(
            "Value", format="%.6f")})
    if st.button("Save values", type="primary"):
        novo = d03.copy()
        for _, r in editado.iterrows():
            alvo = (novo["IDV"] == idv) & (novo["IDVP"] == int(r["IDVP"]))
            novo.loc[alvo, "GC"] = float(r["Stored"] or 0.0)
            novo.loc[alvo, "GCText"] = r["Text"] if pd.notna(r["Text"]) else None
        state.write_table("D03", novo)
        st.success("Saved. Everything downstream was recalculated.")
        st.rerun()
else:
    components.table(exo[["IDVP", "Parameter", "Unit", "Stored", "Text"]])

st.subheader("Endogenous — computed from the above")
components.table(endo[["IDVP", "Parameter", "Unit", "Computed", "Stored",
                       "IsCalculated", "Equation"]])
st.caption("**Computed** is what the equation gives for the current values. "
           "**Stored** is what the project file holds; when `IsCalculated` is "
           "0, the stored value was supplied and it is the one used.")

resultado = resultados.get((idv, 1))
if resultado is not None:
    st.divider()
    st.subheader("Resulting mass")
    col1, col2 = st.columns(2)
    col1.metric("Vehicle mass (kg)",
                components.number(resultado["totals"]["MassIDV"], 1))
    col2.metric("Cradle to gate (kg CO₂e)",
                components.number(resultado["totals"]["GHGCradleToGate"], 1))
    components.how_was_this_calculated(
        "Mass of one subgroup",
        "ME = MR · (GC / GCR)^Beta · fLM",
        {"MR": "reference mass of the subgroup (P06)",
         "GC": "value of the dimensioning parameter (D03, via P08)",
         "GCR": "reference value of that parameter (P06)",
         "Beta": "scaling exponent (P06)",
         "fLM": "lightweighting factor (module M5, 1 in this version)"},
        "§8.1")
    components.table(resultado["C01"][["IDSG", "IDVP", "GC", "Beta", "GCR",
                                       "MR", "fLM", "ME"]])
