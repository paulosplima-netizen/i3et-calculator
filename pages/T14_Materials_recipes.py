"""T14 · Materials and recipes — the material composition of each GREET group.

Reference recipes are read-only. A copy of your own (prefix U-) can be edited; a draft
whose groups do not close on 1 (or 0) can be saved but cannot be chosen in an analysis.
The illustrative mass is the share times a reference mass, not the vehicle's mass.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import formatting as fm
from core import loader, materials, run, user_recipes
from ui import flow, navigation

ROLE = {"material": "Material", "process": "Process", "breakdown": "Breakdown"}


def _bill(conn, ctx, flow) -> None:
    """Accumulated material list of one vehicle of a frozen run (all groups together)."""
    st.caption("Mass of each material summed over all GREET groups of a vehicle. It needs a "
               "frozen run, because the masses depend on the vehicle; the recipe used is the "
               "one frozen with that run, not the one chosen above.")
    ida = flow.pick_analysis(conn, key="t14_analysis")
    rs = flow.runs(conn, ida) if ida else []
    if not rs:
        st.info("No frozen run yet. Use **Validate and Freeze Inputs** (T41).")
        return
    ids = [r["RunID"] for r in rs]
    labels = {r["RunID"]: f"S{r['RunSeq']} · {r['FrozenAt']} · {r['Status']}" for r in rs}
    rid = st.selectbox("Run", ids, format_func=labels.get, index=len(ids) - 1, key="t14_run")
    try:
        detail = run.recompute(conn, ctx.path, rid)
    except ValueError as exc:                                  # I53
        st.error(str(exc))
        return
    if not detail:
        st.info("This run has no vehicles.")
        return
    key = st.selectbox("Vehicle", list(detail), key="t14_vehicle")
    res = detail[key][1]
    with_bat = st.checkbox("Include the traction battery materials", value=True)
    has_bat = len(res["C07"]) > 0
    if with_bat and not has_bat:
        st.caption("This vehicle has no traction battery composition.")
    bill = materials.vehicle_bill(res["C03"], res["C07"],
                                                   include_battery=with_bat)
    fmt_ = flow.display_format(conn)
    show = bill.rename(columns={"MassVehicleKg": "Vehicle (kg)", "MassBatteryKg": "Battery (kg)",
                                "MassKg": "Total (kg)", "ShareOfMass": "Share of total"})
    show["Share of total"] = fm.frame(bill, {"ShareOfMass": "share"}, fmt_)["ShareOfMass"]
    c1, c2 = st.columns(2)
    c1.metric("Total mass in the list (kg)", f"{bill['MassKg'].sum():,.1f}")
    c2.metric("Battery included", "Yes" if with_bat and has_bat else "No")
    st.dataframe(show.drop(columns=["IDM"]).assign(IDM=bill["IDM"])[
        ["IDM", "DsM", "Vehicle (kg)", "Battery (kg)", "Total (kg)", "Share of total"]],
        hide_index=True, use_container_width=True)
    st.caption("Only lines that count as mass; processes and breakdowns are not listed. "
               "Without the battery the total is the glider and powertrain mass.")


ctx = flow.begin("Materials and recipes", edit=True)
author = st.sidebar.text_input("Your name", value=st.session_state.get("author", ""),
                               key="author")
with flow.connect(ctx.path) as conn:
    base = loader.load_sqlite(ctx.path)
    p09 = base["P09"][["IDM", "DsM", "ShareRole"]]
    groups = base["P04"][["IDGG", "DsGG"]]
    own = pd.read_sql_query("SELECT * FROM D13_UserRecipe ORDER BY IDVMRU", conn)
    d14 = pd.read_sql_query("SELECT * FROM D14_UserMaterialShare", conn)
    recipes = pd.concat([
        base["P15"][~base["P15"]["IDVMR"].isin(own["IDVMRU"])][["IDVMR", "DsVMR"]]
        .assign(Kind="reference"),
        own.rename(columns={"IDVMRU": "IDVMR", "DsVMRU": "DsVMR"})[["IDVMR", "DsVMR"]]
        .assign(Kind="yours")], ignore_index=True)

    def shares_of(idvmr: str) -> pd.DataFrame:
        if idvmr in set(own["IDVMRU"]):
            sub = d14[d14["IDVMRU"] == idvmr].rename(columns={"IDVMRU": "IDVMR"})
        else:
            sub = base["P16"][base["P16"]["IDVMR"] == idvmr]
        return sub[["IDGG", "IDM", "MshareGG"]].merge(p09, on="IDM", how="left")

    tab_r, tab_c, tab_e = st.tabs(["Recipe", "Compare", "Copy and edit"])

    with tab_r:
        chosen = st.selectbox("Recipe", list(recipes["IDVMR"]), format_func=lambda r: (
            f"{r} · {recipes.set_index('IDVMR').loc[r, 'DsVMR']}"))
        sh = shares_of(chosen)
        status = []
        for g, sub in sh.groupby("IDGG"):
            total = float(sub.loc[sub["ShareRole"] == "material", "MshareGG"].sum())
            state = ("not applicable (all zero) — verify applicability" if abs(total) <= 1e-6
                     else "closed" if abs(total - 1) <= 1e-6 else "DOES NOT CLOSE")
            status.append({"Group": g, "Sum of material shares": round(total, 6),
                           "Check": state})
        st.dataframe(pd.DataFrame(status), hide_index=True, use_container_width=True)
        ALL = "__all__"
        group = st.selectbox("Group", [ALL] + list(groups["IDGG"]), format_func=lambda g: (
            "All groups (vehicle bill of materials)" if g == ALL
            else f"{g} · {groups.set_index('IDGG').loc[g, 'DsGG']}"))
        if group == ALL:
            _bill(conn, ctx, flow)
        else:
            hide_zero = st.checkbox("Hide zero entries", value=True)
            one = sh[sh["IDGG"] == group].copy()
            one["Role"] = one["ShareRole"].map(ROLE)
            fmt_ = flow.display_format(conn)
            share_col = f"Share ({fm.unit('share', fmt_) or 'fraction'})"
            one[share_col] = fm.frame(one, {"MshareGG": "share"}, fmt_)["MshareGG"]
            if hide_zero:
                one = one[one["MshareGG"] > 0]
            st.dataframe(one[["IDM", "DsM", "Role", share_col]], hide_index=True,
                         use_container_width=True)
            st.caption("Origin: " + str(recipes.set_index("IDVMR").loc[chosen, "DsVMR"])
                       + ". Negative shares of the workbook were stored as zero and the group "
                         "renormalized (divergence D8).")
        if chosen in set(own["IDVMRU"]):
            problems = user_recipes.check(conn, chosen)
            if problems:
                st.error("Draft cannot be chosen in an analysis: " + "; ".join(problems))
            else:
                st.success("Valid: it can be chosen in an analysis.")

    with tab_c:
        other = st.selectbox("Compare with", list(recipes["IDVMR"]), key="cmp")
        a = shares_of(chosen).groupby(["IDGG", "IDM"])["MshareGG"].sum()
        b = shares_of(other).groupby(["IDGG", "IDM"])["MshareGG"].sum()
        diff = pd.DataFrame({"A": a, "B": b}).fillna(0.0)
        fmt_ = flow.display_format(conn)
        raw = diff["B"] - diff["A"]
        diff["Diff (pp)" if fmt_.share_as == "percent" else "Diff"] = fm.frame(
            pd.DataFrame({"d": raw}), {"d": "share"}, fmt_)["d"]
        diff = diff[raw.abs() > 0].reset_index()
        st.dataframe(diff, hide_index=True, use_container_width=True)

    with tab_e:
        if ctx.can_edit:
            with st.form("copy"):
                c1, c2 = st.columns(2)
                new_id = c1.text_input("Identifier (starts with U-)", value="U-1")
                src = c2.selectbox("Copy from", list(base["P15"][
                    ~base["P15"]["IDVMR"].isin(own["IDVMRU"])]["IDVMR"]))
                name = st.text_input("Name")
                notes = st.text_area("Notes and sources")
                if st.form_submit_button("Create copy"):
                    try:
                        user_recipes.copy_recipe(conn, new_id, src, name, author, notes)
                        st.success(f"{new_id} created.")
                    except ValueError as e:
                        st.error(str(e))
        mine = list(pd.read_sql_query("SELECT IDVMRU FROM D13_UserRecipe", conn)["IDVMRU"])
        if mine and ctx.can_edit:
            rid = st.selectbox("Your recipe", mine)
            g = st.selectbox("Group to edit", list(groups["IDGG"]), key="eg")
            sh2 = pd.read_sql_query(
                "SELECT d.IDM, p.DsM, p.ShareRole, d.MshareGG, d.SourceU FROM "
                "D14_UserMaterialShare d JOIN P09_Material p USING (IDM) WHERE d.IDVMRU = ? "
                "AND d.IDGG = ? ORDER BY d.IDM", conn, params=(rid, g))
            edited = st.data_editor(sh2, hide_index=True, use_container_width=True,
                                    disabled=["IDM", "DsM", "ShareRole"], key=f"ed_{rid}_{g}")
            c1, c2 = st.columns(2)
            if c1.button("Save group"):
                try:
                    for old, new in zip(sh2.itertuples(), edited.itertuples()):
                        if abs(old.MshareGG - new.MshareGG) > 1e-12 or old.SourceU != new.SourceU:
                            user_recipes.set_share(conn, rid, g, new.IDM, float(new.MshareGG),
                                                   source=new.SourceU or "", author=author)
                    st.success("Saved.")
                except ValueError as e:
                    st.error(str(e))
            if c2.button("Normalize material shares"):
                st.success("Normalized." if user_recipes.normalize_group(
                    conn, rid, g, author=author) else "Nothing to normalize (sum is zero).")
            st.caption("Normalizing only acts on material shares, never on process or breakdown.")

navigation.link("T04")
