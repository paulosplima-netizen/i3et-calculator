"""Menus and shortcuts (docs/06, section 3).

Four menus plus global access. Each screen has one menu of origin; the other
ways in are shortcuts (`st.page_link`). Only delivered screens are listed.
T18 and T15 are the 0.9.0 Results and Emission factors screens, unchanged.
"""

from __future__ import annotations

import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError

#: (key, file, title, icon)
SCREENS = {
    "T01": ("pages/T01_Home.py", "Home", "🏠"),
    "T02": ("pages/T02_Vehicle_picker.py", "Vehicle picker", "🔎"),
    "T03": ("pages/T03_Project_configuration.py", "Project Configuration", "🧭"),
    "T04": ("pages/T04_Selected_parameters.py", "Selected Parameters", "🎚"),
    "T10": ("pages/T10_Vehicle_parameters.py", "Vehicle parameters", "🔧"),
    "T11": ("pages/T11_Default_parameters.py", "Default parameters", "📐"),
    "T41": ("pages/T41_Validate_and_freeze.py", "Validate and Freeze Inputs", "❄"),
    "T05": ("pages/T05_Dashboard.py", "Dashboard", "📊"),
    "T06": ("pages/T06_Multiple_projects.py", "Multiple Projects", "🗂"),
    "T18": ("pages/5_Results.py", "Manufacturing results", "🏗"),
    "T09": ("pages/T09_Market_vehicles.py", "Market Vehicles", "🚗"),
    "T15": ("pages/6_Emission_factors.py", "Emission factors", "🏭"),
    "T07": ("pages/T07_Equations_and_glossary.py", "Equations & glossary", "📖"),
    "T08": ("pages/T08_Export.py", "Export", "📤"),
}

MENUS = {
    "Home": ["T01", "T02", "T03"],
    "Analysis Parameters Setup": ["T04", "T10", "T11", "T41"],
    "Results": ["T05", "T06", "T18"],
    "Auxiliary Data": ["T09", "T15"],
    "Help and export": ["T07", "T08"],
}


def pages() -> dict[str, list]:
    out = {}
    for menu, keys in MENUS.items():
        out[menu] = [st.Page(SCREENS[k][0], title=f"{k} · {SCREENS[k][1]}", icon=SCREENS[k][2],
                             default=(k == "T01")) for k in keys]
    return out


def link(key: str, label: str | None = None) -> None:
    """A shortcut to another screen."""
    path, title, icon = SCREENS[key]
    text = label or f"{key} · {title}"
    try:
        st.page_link(path, label=text, icon=icon)
    except StreamlitPageNotFoundError:
        # Fora do app.py (um teste que abre a pagina sozinha) nao ha registro de paginas.
        st.caption(f"→ {text}")
