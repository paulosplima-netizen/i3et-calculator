"""Load the reference base and a project into plain DataFrames.

This is the only module in `core` that touches a file. Everything downstream
receives tables and returns tables, which is what lets the same code run in the
web app, in a notebook and in the tests.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

import pandas as pd

from . import schema


@dataclass
class Base:
    """The tables of one database, keyed by short name (P06, D03, ...)."""

    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    param_hash: str | None = None

    def __getitem__(self, name: str) -> pd.DataFrame:
        return self.tables[name]

    def __contains__(self, name: str) -> bool:
        return name in self.tables

    def get(self, name: str, default=None):
        return self.tables.get(name, default)


def load_sqlite(path: str) -> Base:
    """Read every P, D and metadata table of a database file."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    tables = {}
    for full in schema.PARAM_TABLES + schema.SCENARIO_TABLES:
        short = full.split("_")[0]
        tables[short] = pd.read_sql_query(f"SELECT * FROM {full}", conn)
    param_hash = None
    try:
        row = conn.execute(
            "SELECT Value FROM M00_BaseInfo WHERE Key = 'ParamBaseHash'").fetchone()
        param_hash = row[0] if row else None
    except sqlite3.Error:
        pass
    conn.close()
    return Base(tables=tables, param_hash=param_hash)


def effective_emission_factors(base: Base) -> pd.DataFrame:
    """P11 extended with the user's own versions, user taking precedence.

    Returns columns IDM, IDEFV, EF, EFnotes, IsUserDefined. A NULL EF is kept as
    NULL: it means "no factor published", which is not zero emissions.
    """
    p11 = base["P11"][["IDM", "IDEFV", "EF", "EFnotes"]].copy()
    p11["IsUserDefined"] = 0
    parts = [p11]

    d04 = base.get("D04")
    d05 = base.get("D05")
    if d05 is not None and len(d05):
        own = d05[["IDM", "IDEFV", "EF", "EFnotes"]].copy()
        own["IsUserDefined"] = 1
        parts.append(own)
    if d04 is not None and len(d04):
        for _, v in d04.iterrows():
            if not v.get("BasedOnIDEFV"):
                continue
            inherited = p11[p11["IDEFV"] == v["BasedOnIDEFV"]].copy()
            if d05 is not None and len(d05):
                already = set(d05.loc[d05["IDEFV"] == v["IDEFV"], "IDM"])
                inherited = inherited[~inherited["IDM"].isin(already)]
            inherited["IDEFV"] = v["IDEFV"]
            inherited["IsUserDefined"] = 1
            parts.append(inherited)

    out = pd.concat(parts, ignore_index=True)
    return out.drop_duplicates(subset=["IDM", "IDEFV"], keep="last")
