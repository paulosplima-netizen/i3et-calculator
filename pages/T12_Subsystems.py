"""T12 · Subsystems — each vehicle subsystem, its parameter and its GREET group.

Read-only reference: the correlation of the M1 module (subgroup → generic group →
GREET group, and the vehicle parameter used as GC). The workbook prevails.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import loader
from ui import flow, navigation

ctx = flow.begin("Subsystems")
with flow.connect(ctx.path):
    base = loader.load_sqlite(ctx.path)
    df = (base["P02"].merge(base["P08"], on="IDSG", how="left")
          .merge(base["P03"], on="IDG", how="left")
          .merge(base["P04"][["IDGG", "DsGG"]], on="IDGG", how="left")
          .merge(base["P07"][["IDVP", "DsVP", "utVP"]], on="IDVP", how="left"))
    gg = st.multiselect("GREET group", sorted(df["IDGG"].dropna().unique()))
    text = st.text_input("Search subsystem")
    if gg:
        df = df[df["IDGG"].isin(gg)]
    if text:
        df = df[df["DsSG"].str.contains(text, case=False, na=False)]
    cols = [c for c in ("IDSG", "DsSG", "IDG", "DsG", "IDGG", "DsGG", "IDVP", "DsVP", "utVP",
                        "ExcludedVPT", "SourceRow", "NotesSG") if c in df.columns]
    st.dataframe(df[cols], hide_index=True, use_container_width=True)
    st.caption(f"{len(df)} subsystems. In the workbook, ID 23 appears twice in M1 (row 36 is "
               "IDSG 23; row 37 is IDSG 43): a defect of the sheet, not reproduced here.")
    pending = df["IDGG"].isna().sum()
    if pending:
        st.warning(f"{int(pending)} subsystems have no GREET group.")
    by_group = df.groupby("IDGG", dropna=False).size().reset_index(name="Subsystems")
    st.dataframe(pd.DataFrame(by_group), hide_index=True, use_container_width=True)

navigation.link("T13")
