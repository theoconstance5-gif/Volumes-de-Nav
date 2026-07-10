"""
Thème visuel partagé — identité "La Vague Normande Sport".

Palette (extraite du logo du club) :
  - Noir profond       #212121  (fond, sidebar, texte fort)
  - Corail vif         #FF5562  (accent primaire, dégradé de la bannière)
  - Corail clair       #FF7E87  (fin de dégradé, survols)
  - Corail sourd       #E5495A  (variante foncée pour texte sur fond clair)
  - Blanc              #FFFFFF  (fond de page, cartes)
  - Gris ardoise       #6B6B6B  (texte secondaire)

Typographies :
  - Titres  : "Space Grotesk" (géométrique, énergique — proche de l'esprit du logo)
  - Corps   : "Inter" (lisible, neutre)
  - Données : "JetBrains Mono" (chiffres alignés, esprit carnet de mesures)
"""

import base64
from pathlib import Path

import streamlit as st

PALETTE = {
    "black": "#212121",
    "coral": "#FF5562",
    "coral_light": "#FF7E87",
    "coral_dark": "#E5495A",
    "white": "#FFFFFF",
    "slate": "#6B6B6B",
    "card": "#FFFFFF",
    "border": "#EAEAEA",
}

# Palette dédiée aux graphiques : dégradé corail + neutres du logo, pour rester
# dans la charte tout en gardant des séries lisibles.
CHART_COLORS = [
    "#FF5562",  # corail principal
    "#212121",  # noir
    "#FF9AA2",  # corail très clair
    "#8C8C8C",  # gris moyen
    "#E5495A",  # corail foncé
    "#C9C9C9",  # gris clair
    "#FFC6CB",  # rose pâle
]

ASSETS_DIR = Path(__file__).parent / "assets"


@st.cache_data
def _img_b64(filename: str) -> str:
    path = ASSETS_DIR / filename
    return base64.b64encode(path.read_bytes()).decode()


def inject_css():
    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
        <style>
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}
        .stApp {{
            background-color: {PALETTE['white']};
        }}
        h1, h2, h3, h4 {{
            font-family: 'Space Grotesk', sans-serif !important;
            color: {PALETTE['black']} !important;
            letter-spacing: -0.01em;
        }}
        [data-testid="stMetricValue"] {{
            font-family: 'JetBrains Mono', monospace;
            color: {PALETTE['black']};
        }}
        [data-testid="stMetricLabel"] {{
            color: {PALETTE['slate']};
        }}
        [data-testid="stMetric"] {{
            background: {PALETTE['white']};
            border: 1px solid {PALETTE['border']};
            border-left: 4px solid {PALETTE['coral']};
            border-radius: 10px;
            padding: 12px 16px;
        }}
        section[data-testid="stSidebar"] {{
            background-color: {PALETTE['black']};
        }}
        section[data-testid="stSidebar"] * {{
            color: {PALETTE['white']} !important;
        }}
        section[data-testid="stSidebar"] .stRadio label:hover {{
            color: {PALETTE['coral_light']} !important;
        }}
        section[data-testid="stSidebar"] hr {{
            border-color: #3a3a3a;
        }}
        .voile-header {{
            display: flex;
            align-items: center;
            gap: 20px;
            padding: 22px 28px;
            background: linear-gradient(120deg, #1a1a1a 0%, {PALETTE['black']} 100%);
            border-radius: 14px;
            margin-bottom: 24px;
            border: 1px solid #333333;
        }}
        .voile-header img {{
            height: 48px;
            width: auto;
            object-fit: contain;
        }}
        .voile-header h1 {{
            color: {PALETTE['white']} !important;
            margin: 0;
            font-size: 26px;
        }}
        .voile-header p {{
            color: #B8B8B8;
            margin: 2px 0 0 0;
            font-size: 14px;
        }}
        .voile-card {{
            background: {PALETTE['card']};
            border: 1px solid {PALETTE['border']};
            border-radius: 12px;
            padding: 18px 20px;
        }}
        .voile-divider {{
            border: none;
            border-top: 1px dashed {PALETTE['border']};
            margin: 22px 0;
        }}
        .stButton>button, .stDownloadButton>button {{
            background-color: {PALETTE['coral']};
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 500;
        }}
        .stButton>button:hover {{
            background-color: {PALETTE['black']};
            color: {PALETTE['coral_light']};
        }}
        .stButton [kind="primary"] {{
            background-color: {PALETTE['coral_dark']};
        }}
        div[data-baseweb="tag"] {{
            background-color: {PALETTE['coral']} !important;
        }}
        .stTabs [aria-selected="true"] {{
            color: {PALETTE['coral_dark']} !important;
            border-bottom-color: {PALETTE['coral']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_logo():
    """Affiche le logo du club en haut de la barre latérale."""
    try:
        st.logo(str(ASSETS_DIR / "logo_bandeau.png"), icon_image=str(ASSETS_DIR / "logo_icon.png"))
    except Exception:
        pass


def page_header(icon: str, title: str, subtitle: str = ""):
    """En-tête de page avec dégradé corail et logo rond du club."""
    try:
        logo_b64 = _img_b64("logo_bandeau.png")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="logo">'
    except Exception:
        logo_html = f'<div style="font-size:32px;">{icon}</div>'

    st.markdown(
        f"""
        <div class="voile-header">
            {logo_html}
            <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def require_coach_auth():
    """
    Protège une page derrière un mot de passe entraîneur partagé, défini
    dans st.secrets["COACH_PASSWORD"]. Si aucun mot de passe n'est
    configuré (ex : usage local sans secrets.toml), la page reste ouverte.
    À utiliser en tout début de page pour les sections réservées aux coachs
    (Saisie, Analyse, Configuration, Analyse du debrief).
    """
    try:
        expected = st.secrets.get("COACH_PASSWORD")
    except Exception:
        expected = None

    if not expected:
        return  # pas de mot de passe configuré -> accès libre (dev local)

    if st.session_state.get("coach_authenticated"):
        return

    st.markdown("### 🔒 Accès entraîneurs")
    st.caption("Cette page est réservée aux entraîneurs.")
    pwd = st.text_input("Mot de passe", type="password", key="coach_password_input")
    if st.button("Valider", key="coach_password_submit"):
        if pwd == expected:
            st.session_state["coach_authenticated"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    st.stop()
