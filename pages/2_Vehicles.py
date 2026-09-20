"""Screen 2 — the vehicles in the project."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import components, state

atual = components.page("Vehicles", "§7")
base, resultados, log = atual

d01 = base["D01"]
d02 = base["D02"]
visao = d01.merge(d02, on="IDV", how="left")
visao["Source"] = visao["IsUserDefined"].map({0: "reference", 1: "yours"})

st.write("The twelve reference vehicles come with the base and are never "
         "modified. Vehicles you create are marked as yours, and live only in "
         "your project file.")

components.table(visao[["IDV", "DsV", "IDVPT", "IDVDT", "IDVS", "IDLR",
                        "Source", "IDMPV", "IDVMR", "IDEFV", "IDAPV",
                        "Boundary"]])

st.divider()
st.subheader("Create a vehicle")
st.write("A new vehicle starts as a copy of an existing one of the same "
         "powertrain, with every inherited value marked, so you change what "
         "differs instead of filling in forty parameters.")

with st.form("novo_veiculo"):
    col1, col2, col3 = st.columns(3)
    modelo = col1.selectbox("Copy from", options=d01["DsV"].tolist())
    nome = col2.text_input("Name", value="MEU01")
    porte = col3.selectbox("Size", options=sorted(base["P14"]["IDVS"].unique()))
    col4, col5, col6 = st.columns(3)
    trem = col4.selectbox("Powertrain", options=sorted(base["P12"]["IDVPT"].unique()))
    carroceria = col5.selectbox("Body", options=sorted(base["P13"]["IDVDT"].unique()))
    receitas = base["P15"]
    receita = col6.selectbox(
        "Material recipe", options=receitas["IDVMR"].tolist(),
        help="Which composition to apply. The Scenario screen explains the "
             "difference between the two families.")
    criar = st.form_submit_button("Create", type="primary")

if criar:
    if nome.strip() in set(d01["DsV"]):
        st.error(f"There is already a vehicle named {nome}.")
    else:
        origem = d01[d01["DsV"] == modelo].iloc[0]
        novo_id = int(d01["IDV"].max()) + 1
        linha = {"IDV": novo_id, "DsV": nome.strip(), "IDVPT": trem,
                 "IDVDT": carroceria, "IDVS": porte, "IDLR": origem["IDLR"],
                 "IsUserDefined": 1,
                 "NotesIDV": f"Criado a partir de {modelo}."}
        state.write_table("D01", pd.concat(
            [d01, pd.DataFrame([linha])], ignore_index=True))

        d03 = base["D03"]
        copia = d03[d03["IDV"] == int(origem["IDV"])].copy()
        copia["IDV"] = novo_id
        state.write_table("D03", pd.concat([d03, copia], ignore_index=True))

        cen = d02[d02["IDV"] == int(origem["IDV"])].iloc[0].to_dict()
        cen.update({"IDV": novo_id, "IDEA": 1, "IDVMR": receita,
                    "NotesIDEA": f"Criado a partir de {modelo}."})
        state.write_table("D02", pd.concat(
            [d02, pd.DataFrame([cen])], ignore_index=True))
        st.success(f"{nome} created. Open **Vehicle parameters** to adjust it.")
        st.rerun()

proprios = d01[d01["IsUserDefined"] == 1]
if len(proprios):
    st.divider()
    st.subheader("Remove a vehicle of yours")
    alvo = st.selectbox("Vehicle", options=proprios["DsV"].tolist())
    if st.button("Remove"):
        idv = int(proprios[proprios["DsV"] == alvo].iloc[0]["IDV"])
        state.write_table("D02", d02[d02["IDV"] != idv])
        state.write_table("D03", base["D03"][base["D03"]["IDV"] != idv])
        state.write_table("D01", d01[d01["IDV"] != idv])
        st.rerun()
