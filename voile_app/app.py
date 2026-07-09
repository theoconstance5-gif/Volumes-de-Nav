"""
Point d'entrée de l'application.

Les icônes de menu sont définies ici, en code Python (chaîne UTF-8 dans le
fichier source), plutôt que dans les noms de fichiers des pages. Cela évite
les problèmes d'encodage des émojis dans les noms de fichiers rencontrés sur
certains systèmes Windows selon la configuration régionale.
"""

import streamlit as st

from style import inject_css, sidebar_logo

st.set_page_config(
    page_title="La Vague Normande Sport — Suivi Voile",
    page_icon="assets/logo_icon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("pages/accueil.py", title="Accueil", icon="⛵", default=True),
    st.Page("pages/saisie.py", title="Saisie", icon="📝"),
    st.Page("pages/analyse.py", title="Analyse", icon="📊"),
    st.Page("pages/configuration.py", title="Configuration", icon="⚙️"),
]

inject_css()
sidebar_logo()

pg = st.navigation(pages)
pg.run()
