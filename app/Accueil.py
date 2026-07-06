"""Point d'entrée de l'app : routeur st.navigation + bascule de langue.

    streamlit run app/Accueil.py
"""

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="CritiqueMeta", page_icon="🎮", layout="wide")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import t, lang_selector  # noqa: E402

lang_selector()

pg = st.navigation([
    st.Page("pages/Home.py", title=t("Home", "Accueil"), icon="🏠", default=True),
    st.Page("pages/Distributions.py", title=t("Distributions", "Distributions"), icon="📊"),
    st.Page("pages/Platforms.py", title=t("Platforms", "Plateformes"), icon="🕹️"),
    st.Page("pages/Games.py", title=t("Games", "Jeux"), icon="🎯"),
    st.Page("pages/Critics.py", title=t("Critics", "Critiques"), icon="📰"),
    st.Page("pages/Developers.py", title=t("Developers", "Développeurs"), icon="🏗️"),
    st.Page("pages/Trends.py", title=t("Trends", "Tendances"), icon="📈"),
    st.Page("pages/OpenCritic.py", title="OpenCritic", icon="⚖️"),
])
pg.run()
