"""Screen 6 — the published factor versions, and the ones you make.

Documento 1, secao 16.4. A version of your own inherits from a published one
and overrides only the materials you change, which is how the factors of the
Projeto do Berço ao Portão can be used before they are folded into the base.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from core import loader
from ui import components, state

atual = components.page("Emission factors", "§16.4")
base, resultados, log = atual

p10, p11 = base["P10"], base["P11"]
d04, d05 = base["D04"], base["D05"]

st.subheader("Versions in this project")
versoes = pd.concat([
    p10.assign(Source="reference"),
    d04.assign(Source="yours") if len(d04) else
    pd.DataFrame(columns=[*p10.columns, "Source"]),
], ignore_index=True)
components.table(versoes[["IDEFV", "DsEFV", "DateIDEFV", "GWPSet", "Source",
                          "SourceEFV"]])

st.caption("Redistribution of the GREET-derived values is allowed for "
           "non-commercial use, with attribution and the statement that input "
           "values were modified. The licence text of each version is in the "
           "`LicenseEFV` column and travels into every export.")

st.divider()
st.subheader("Browse the factors")
escolhida = st.selectbox("Version", options=list(versoes["IDEFV"]))
efetivos = loader.effective_emission_factors(base)
desta = efetivos[efetivos["IDEFV"] == escolhida].merge(
    base["P09"][["IDM", "DsM", "EFBasis"]], on="IDM", how="left")
sem_fator = desta["EF"].isna().sum()
col1, col2 = st.columns(2)
col1.metric("Materials in this version", len(desta))
col2.metric("Without a published factor", int(sem_fator))
components.table(desta[["IDM", "DsM", "EFBasis", "EF", "IsUserDefined",
                        "EFnotes"]])
if sem_fator:
    st.caption("A missing factor is absence of data, never zero emissions: the "
               "mass of those materials is reported in `MassNoFactor` on every "
               "result.")

st.divider()
st.subheader("Create a version of your own")
st.write("It starts from a published version and keeps everything you do not "
         "change. Saying where your values come from is required — a factor "
         "without provenance is not usable by whoever reads the result.")

with st.form("nova_versao"):
    col1, col2 = st.columns(2)
    nome = col1.text_input("Identifier", value="MEUS-FATORES",
                           help="Short, and unique in this project.")
    origem = col2.selectbox("Inherit from", options=list(p10["IDEFV"]))
    descricao = st.text_input("Description", value="Fatores próprios")
    fonte = st.text_area(
        "Where do these values come from?",
        placeholder="Ex.: inventário do fornecedor, medição própria, artigo "
                    "com DOI, versão do GREET não incluída na base…")
    criar = st.form_submit_button("Create version", type="primary")

if criar:
    if not fonte.strip():
        st.error("Provenance is required.")
    elif nome.strip() in set(versoes["IDEFV"]):
        st.error(f"There is already a version called {nome}.")
    else:
        linha = {"IDEFV": nome.strip(), "DsEFV": descricao.strip(),
                 "DateIDEFV": dt.date.today().isoformat(),
                 "GWPSet": p10[p10["IDEFV"] == origem].iloc[0]["GWPSet"],
                 "SourceEFV": fonte.strip(),
                 "LicenseEFV": "Definido pelo usuario deste projeto.",
                 "BasedOnIDEFV": origem}
        state.write_table("D04", pd.concat(
            [d04, pd.DataFrame([linha])], ignore_index=True))
        st.success(f"{nome} created. It inherits every factor of {origem}; "
                   "override below the ones you want to change.")
        st.rerun()

if len(d04):
    st.divider()
    st.subheader("Override factors in one of your versions")
    minha = st.selectbox("Your version", options=list(d04["IDEFV"]))
    materiais = base["P09"][["IDM", "DsM"]]
    col1, col2 = st.columns([2, 1])
    idm = col1.selectbox(
        "Material", options=list(materiais["IDM"]),
        format_func=lambda m: f"{m} · {materiais[materiais['IDM'] == m].iloc[0]['DsM']}")
    valor = col2.number_input("kg CO₂e per unit", min_value=0.0, value=0.0,
                              format="%.6f")
    nota = st.text_input("Provenance of this value", key="nota_fator")
    if st.button("Save factor"):
        if not nota.strip():
            st.error("Provenance is required for each value.")
        else:
            novo = d05[~((d05["IDEFV"] == minha) & (d05["IDM"] == idm))] \
                if len(d05) else d05
            linha = {"IDM": idm, "IDEFV": minha, "EF": float(valor),
                     "EFnotes": nota.strip()}
            state.write_table("D05", pd.concat(
                [novo, pd.DataFrame([linha])], ignore_index=True))
            st.success("Saved. Any scenario using this version was recalculated.")
            st.rerun()

    if len(d05):
        st.caption("Values you overrode:")
        components.table(d05[d05["IDEFV"] == minha])
