"""T15 · Emission factors — the reference versions, and the ones you make.

The reference base file is never edited. Typed lists (and lists of your own) can be
corrected: the new value is kept in your project, over the base value, and every change
is logged with author, date and reason (D19). Published lists cite a source and are
locked: copy one to a typed version first. A missing factor (ND) is absence of data,
never zero.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import ef_edit, loader
from core import formatting as fm
from ui import flow, navigation

ctx = flow.begin("Emission factors", edit=True)
author = st.sidebar.text_input("Your name", value=st.session_state.get("author", ""),
                               key="author")
with flow.connect(ctx.path) as conn:
    base = loader.load_sqlite(ctx.path)
    p10 = base["P10"]
    d04 = base["D04"] if "D04" in base and len(base["D04"]) else pd.DataFrame(columns=p10.columns)
    versions = pd.concat([p10.assign(Source="reference"), d04.assign(Source="yours")],
                         ignore_index=True)
    eff = loader.effective_emission_factors(base)
    materials = base["P09"][["IDM", "DsM", "EFBasis"]]
    gwp = dict(zip(versions["IDEFV"], versions["GWPSet"]))

    tab_f, tab_c, tab_v, tab_h = st.tabs(["Factors", "Compare versions", "Versions & coverage",
                                          "History"])

    with tab_f:
        chosen = st.selectbox("Version", list(versions["IDEFV"]))
        info = ef_edit.status(conn, chosen)
        mine = info["editable"]
        sub = eff[eff["IDEFV"] == chosen].merge(materials, on="IDM", how="left")
        c1, c2, c3 = st.columns(3)
        c1.metric("Materials", len(sub))
        c2.metric("Without a published factor", int(sub["EF"].isna().sum()))
        c3.metric("Origin", info["label"])
        basis = st.multiselect("Application basis", sorted(sub["EFBasis"].dropna().unique()))
        only_missing = st.checkbox("Only materials without a factor")
        text = st.text_input("Search material")
        if basis:
            sub = sub[sub["EFBasis"].isin(basis)]
        if only_missing:
            sub = sub[sub["EF"].isna()]
        if text:
            sub = sub[sub["DsM"].fillna("").str.contains(text, case=False)
                      | sub["IDM"].astype(str).str.contains(text)]
        st.dataframe(fm.frame(sub[["IDM", "DsM", "EFBasis", "EF", "IsUserDefined", "EFnotes"]],
                              {"EF": "factor"}, flow.display_format(conn)),
                     hide_index=True, use_container_width=True)
        if info["changed"]:
            st.warning(f"{info['changed']} factor(s) of {chosen} were changed in this project; "
                       "results using this list say so, and a frozen run that used it must be "
                       "frozen again (I53).")
        if not mine:
            st.info("Published lists cannot be edited (they cite their source). To change a "
                    "value, copy this list to a typed version in the tab \"Versions & coverage\" "
                    "and edit the copy; the copy keeps the link to the original.")
        elif ctx.can_edit:
            st.subheader(f"Correct a factor in {chosen}")
            idm = st.selectbox("Material", list(materials["IDM"]),
                               format_func=lambda m: f"{m} · "
                               f"{materials.set_index('IDM').loc[m, 'DsM']}")
            inherited = ef_edit.inherited_value(conn, chosen, str(idm))
            st.caption(f"Inherited value: {inherited if inherited is not None else 'no data'}")
            value = st.number_input("kg CO₂e per unit", min_value=0.0, format="%.6f",
                                    value=float(inherited or 0.0))
            reason = st.text_input("Reason and provenance of this value")
            zero = st.checkbox("I confirm an explicit zero (documented above)") \
                if value == 0 else False
            left, right = st.columns(2)
            if left.button("Save factor"):
                try:
                    ef_edit.set_factor(conn, chosen, str(idm), value, reason=reason,
                                       author=author, confirm_zero=zero)
                    st.success("Saved. A run frozen before this change cannot be executed "
                               "any more (I53): freeze the analysis again (T41).")
                except ValueError as e:
                    st.error(str(e))
            if right.button("Use inherited factor"):
                try:
                    done = ef_edit.restore_factor(conn, chosen, str(idm), reason=reason,
                                                  author=author)
                    st.success("Restored." if done else "Nothing to restore for this material.")
                except ValueError as e:
                    st.error(str(e))

    with tab_c:
        a = st.selectbox("Version A", list(versions["IDEFV"]), key="cmp_a")
        b = st.selectbox("Version B", list(versions["IDEFV"]),
                         index=min(1, len(versions) - 1), key="cmp_b")
        table, warning = ef_edit.compare(eff, materials, a, b, gwp)
        if warning:
            st.warning(warning)
        st.dataframe(fm.frame(table[["IDM", "DsM", "EFBasis", "EF_a", "EF_b", "Diff", "DiffPct"]],
                              {"EF_a": "factor", "EF_b": "factor", "Diff": "factor"},
                              flow.display_format(conn)),
                     hide_index=True, use_container_width=True)

    with tab_v:
        cover = eff.groupby("IDEFV")["EF"].agg(Materials="size",
                                               Available=lambda s: int(s.notna().sum()))
        cover["Missing (ND)"] = cover["Materials"] - cover["Available"]
        shown = versions.merge(cover, left_on="IDEFV", right_index=True, how="left")
        st.dataframe(shown[["IDEFV", "DsEFV", "Source", "Origin", "GWPSet", "DateIDEFV",
                            "Materials", "Available", "Missing (ND)", "SourceEFV"]],
                     hide_index=True, use_container_width=True)
        st.caption("Zero only with a documented override; bases are never mixed in a sum; "
                   "IDs 87–97 detail the battery chemistry; end-of-life belongs to T17.")
        if ctx.can_edit:
            st.subheader("Copy a list to a typed version")
            with st.form("copy_version"):
                c1, c2 = st.columns(2)
                src_id = c1.selectbox("Copy from", list(p10["IDEFV"]))
                new_id = c2.text_input("Identifier of the copy", value="TYPED-COPY")
                why = st.text_area("Why do you need to change values? (required)")
                if st.form_submit_button("Copy"):
                    try:
                        ef_edit.copy_to_typed(conn, src_id, new_id, reason=why, author=author)
                        st.success(f"{new_id} created from {src_id}; edit it in the tab Factors.")
                    except ValueError as e:
                        st.error(str(e))
            st.subheader("Create a version of your own")
            with st.form("new_version"):
                c1, c2 = st.columns(2)
                name = c1.text_input("Identifier", value="MY-FACTORS")
                origin = c2.selectbox("Inherit from", list(p10["IDEFV"]))
                desc = st.text_input("Description", value="Own factors")
                source = st.text_area("Where do these values come from? (required)")
                if st.form_submit_button("Create version"):
                    try:
                        ef_edit.create_version(conn, name, desc, origin, source, author)
                        st.success(f"{name} created; it inherits every factor of {origin}.")
                    except ValueError as e:
                        st.error(str(e))

    with tab_h:
        log = pd.read_sql_query("SELECT ChangedAt, IDEFV, IDM, Action, OldEF, NewEF, Author, "
                                "Reason FROM D19_EFChangeLog ORDER BY IDLog DESC", conn)
        st.caption("The history and the corrections keep the full precision of the values.")
        st.dataframe(log, hide_index=True, use_container_width=True)
        st.download_button("Download CSV", log.to_csv(index=False), file_name="ef_history.csv",
                           mime="text/csv")
        st.subheader("Corrections to take back to the workbook and the base")
        corr = ef_edit.corrections(conn)
        st.dataframe(corr, hide_index=True, use_container_width=True)
        st.download_button("Download corrections (CSV)", corr.to_csv(index=False),
                           file_name="ef_corrections.csv", mime="text/csv")

navigation.link("T18")
