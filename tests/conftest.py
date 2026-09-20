"""Shared fixtures.

The reference database and the i3ET fixture are read once per session: they are
read-only, and reloading them for every test would make the suite slow enough
that people stop running it.
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from core import loader  # noqa: E402

DB = os.path.join(REPO, "data", "base_referencia.sqlite")
FIXTURE = os.path.join(REPO, "tests", "fixtures", "i3et_reference.json")
FROZEN = os.path.join(REPO, "tests", "fixtures", "regressao_bp.json")


@pytest.fixture(scope="session")
def base():
    return loader.load_sqlite(DB)


@pytest.fixture(scope="session")
def i3et():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def ef_i3et(i3et):
    """The emission factors the spreadsheet itself was set to."""
    return pd.DataFrame(
        [{"IDM": m, "IDEFV": "FIXTURE", "EF": v, "EFnotes": "i3ET", "IsUserDefined": 0}
         for m, v in i3et["ef_by_material"].items()])


@pytest.fixture(scope="session")
def frozen():
    if not os.path.exists(FROZEN):
        pytest.skip("valores congelados ainda nao gerados")
    with open(FROZEN, encoding="utf-8") as fh:
        return json.load(fh)
