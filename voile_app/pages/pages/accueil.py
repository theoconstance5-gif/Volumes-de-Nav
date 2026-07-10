import streamlit as st
import pandas as pd
from datetime import date, timedelta

from db import init_db, get_db, TrainingSession, Athlete, Group
from style import page_header

init_db()

page_header(
    "⛵", "La Vague Normande Sport",
    "Suivi des volumes d'entraînement — navigue via le menu à gauche"
)

db = get_db()
sessions = db.query(TrainingSession).all()
n_athletes = db.query(Athlete).filter_by(active=True).count()
n_groups = db.query(Group).filter_by(active=True).count()

if not sessions:
    st.info(
        "👋 Bienvenue ! Aucune séance n'est encore enregistrée.\n\n"
        "Commence par vérifier les listes dans **Configuration**, "
        "puis enregistre ta première séance dans **Saisie**."
    )
else:
    last_30 = [s for s in sessions if s.session_date >= date.today() - timedelta(days=30)]
    total_volume = sum(s.duration_hours for s in sessions)
    volume_30 = sum(s.duration_hours for s in last_30)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Séances enregistrées", len(sessions))
    c2.metric("Volume total saison", f"{total_volume:.1f} h")
    c3.metric("Volume 30 derniers jours", f"{volume_30:.1f} h")
    c4.metric("Athlètes actifs", n_athletes)

    st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

    st.markdown("### Dernières séances")
    recent = sorted(sessions, key=lambda s: s.session_date, reverse=True)[:8]

    def _themes_label(s):
        return ", ".join(f"{ts.theme.name} ({ts.hours:g}h)" for ts in s.theme_splits) or "—"

    def _wind_label(s):
        return ", ".join(f"{ws.wind_tranche.label} ({ws.hours:g}h)" for ws in s.wind_splits) or "—"

    rows = [{
        "Date": s.session_date.strftime("%d/%m/%Y"),
        "Groupe": s.group.name if s.group else "—",
        "Lieu": s.spot.name if s.spot else "—",
        "Horaires": f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}",
        "Thématique(s)": _themes_label(s),
        "Vent": _wind_label(s),
        "Durée": f"{s.duration_hours:g} h",
        "Présents": len(s.athletes),
    } for s in recent]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown(
        "➡️ Direction **Analyse** pour explorer, comparer et filtrer toutes ces données."
    )

db.close()

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)
st.caption("Application développée pour le suivi d'entraînement voile — données stockées localement / en base partagée selon configuration.")
