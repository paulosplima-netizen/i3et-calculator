"""Screen 4 — which versions the calculation uses.

Every choice here becomes part of the key of every result, and the screen says
what each one changes. The material recipe gets the most room, because the base
carries two families of them and the difference is not obvious from the name.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import components, state

atual = components.page("Scenario", "§3 and §6")
base, resultados, log = atual

d01 = base["D01"]
d02 = base["D02"]
p15 = base["P15"]

def _familia(idvmr) -> str:
    """Qual das duas familias de receitas, dito em uma palavra."""
    return "Berço ao Portão" if str(idvmr).startswith("PBP_") else "consultoria"


st.write("Two results are comparable only if the versions behind them are "
         "stated. That is why they are a choice, and why they travel with "
         "every exported table.")

nomes = dict(zip(d01["DsV"], d01["IDV"]))
escolhido = st.selectbox("Vehicle", options=list(nomes))
idv = int(nomes[escolhido])
linha = d02[d02["IDV"] == idv].iloc[0]
trem = d01[d01["IDV"] == idv].iloc[0]["IDVPT"]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Material recipe")
    compativeis = p15[p15["IDVPT"] == trem]
    if not len(compativeis):
        st.warning(f"The base has no recipe for a {trem}.")
        compativeis = p15
    opcoes = compativeis["IDVMR"].tolist()
    atual_idx = opcoes.index(linha["IDVMR"]) if linha["IDVMR"] in opcoes else 0
    receita = st.radio(
        "Which composition to apply", options=opcoes, index=atual_idx,
        format_func=lambda v: f"{v}  ·  {_familia(v)}")
    descricao = compativeis[compativeis["IDVMR"] == receita].iloc[0]["DsVMR"]
    st.caption(descricao)
    st.info("**The two families.** `BISD*` is the original recipe, produced by "
            "a consultancy. `PBP_BISD*` is the one the Projeto do Berço ao "
            "Portão built on top of it, adjusting the share of some materials "
            "with data from the Brazilian manufacturers. Same vehicle mass, "
            "different distribution among materials — and therefore different "
            "emissions.")

with col2:
    st.subheader("Versions")
    efvs = list(base["P10"]["IDEFV"]) + list(base["D04"]["IDEFV"])
    idefv = st.selectbox("Emission factors", options=efvs,
                         index=efvs.index(linha["IDEFV"]) if linha["IDEFV"] in efvs else 0)
    fator = base["P10"][base["P10"]["IDEFV"] == idefv]
    if len(fator):
        st.caption(f"{fator.iloc[0]['DsEFV']} · {fator.iloc[0]['GWPSet']}")
    else:
        st.caption("Version you created — see the **Emission factors** screen.")

    mpvs = base["P05"]["IDMPV"].tolist()
    idmpv = st.selectbox("Mass parameters", options=mpvs,
                         index=mpvs.index(linha["IDMPV"]) if linha["IDMPV"] in mpvs else 0)

    apvs = base["P23"]["IDAPV"].tolist()
    idapv = st.selectbox("Assembly parameters", options=apvs,
                         index=apvs.index(linha["IDAPV"]) if linha["IDAPV"] in apvs else 0)
    metodo = base["P23"][base["P23"]["IDAPV"] == idapv].iloc[0]
    st.caption(f"Method `{metodo['Method']}` — {metodo['DsAPV']}")

    fronteira = st.radio(
        "Boundary", options=["MAT_ASM", "MAT"],
        index=0 if linha["Boundary"] == "MAT_ASM" else 1,
        format_func=lambda v: ("materials + assembly (cradle to gate)"
                               if v == "MAT_ASM" else "materials only"))
    st.caption("In `MAT` the assembly is still calculated and reported — it "
               "simply is not added to the total.")

if st.button("Apply to this vehicle", type="primary"):
    novo = d02.copy()
    alvo = novo["IDV"] == idv
    novo.loc[alvo, ["IDVMR", "IDEFV", "IDMPV", "IDAPV", "Boundary"]] = [
        receita, idefv, idmpv, idapv, fronteira]
    state.write_table("D02", novo)
    st.success("Scenario applied. Everything was recalculated.")
    st.rerun()

st.divider()
st.subheader("What each vehicle is set to")
components.table(d02.merge(d01[["IDV", "DsV", "IDVPT"]], on="IDV")[
    ["IDV", "DsV", "IDVPT", "IDMPV", "IDVMR", "IDEFV", "IDAPV", "Boundary"]])

st.divider()
if st.checkbox("Compare the two recipe families on this vehicle"):
    from core import calc

    comparacao = []
    for vmr in compativeis["IDVMR"]:
        gc = {int(r["IDVP"]): float(r["GC"] or 0.0)
              for _, r in base["D03"][base["D03"]["IDV"] == idv].iterrows()}
        bid = base["D03"][(base["D03"]["IDV"] == idv) & (base["D03"]["IDVP"] == 32)]
        bid = bid.iloc[0]["GCText"] if len(bid) else None
        r = calc.calculate_vehicle(
            base, gc, powertrain=trem, battery_id=bid, idmpv=int(idmpv),
            idvmr=vmr, idefv=idefv, idapv=idapv, boundary=fronteira)
        comparacao.append({"Recipe": vmr, "Mass (kg)": r["totals"]["MassIDV"],
                           "Cradle to gate (kg CO₂e)": r["totals"]["GHGCradleToGate"],
                           "kg CO₂e / kg": r["totals"]["GHGperKg"]})
    components.table(pd.DataFrame(comparacao))
    st.caption("Same mass, different emissions: the recipe changes where the "
               "mass goes, not how much of it there is.")
