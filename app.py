"""i3ET Calculator — cradle-to-gate carbon footprint of light vehicles.

Entry point. It only declares the navigation: each screen is its own script
under `pages/`, in the order the analysis happens.

    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

TELAS = [
    ("pages/1_Home.py", "Home", "🏠"),
    ("pages/2_Vehicles.py", "Vehicles", "🚗"),
    ("pages/3_Vehicle_parameters.py", "Vehicle parameters", "🔧"),
    ("pages/4_Scenario.py", "Scenario", "🎛"),
    ("pages/5_Results.py", "Results", "📊"),
    ("pages/6_Emission_factors.py", "Emission factors", "🏭"),
    ("pages/7_Export.py", "Export", "📤"),
]

paginas = [st.Page(caminho, title=titulo, icon=icone, default=(i == 0))
           for i, (caminho, titulo, icone) in enumerate(TELAS)]

st.navigation(paginas).run()
