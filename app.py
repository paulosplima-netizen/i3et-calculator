"""i3ET Calculator — cradle-to-gate carbon footprint of light vehicles.

Entry point. It only declares the navigation: four menus (docs/06, section 3),
each screen its own script under `pages/`.

    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from ui import navigation

st.navigation(navigation.pages()).run()
