import streamlit as st
from datetime import date, time

from db import (
    init_db, get_db, Group, Athlete, Spot, Theme, WindTranche,
    TrainingSession, SessionWindSplit, compute_duration_hours
)
from style import inject_css, page_header, sidebar_logo, PALETTE

st.set_page_config(page_title="Saisie — La Vague Normande Sport", page_icon="assets/logo_icon.png", layout="wide")
inject_css()
sidebar_logo()
init_db()

page_header("📝", "Saisie d'une séance", "Enregistrer une session d'entraînement sur l'eau")

db = get_db()

groups = db.query(Group).filter_by(active=True).order_by(Group.name).all()
spots = db.query(Spot).filter_by(active=True).order_by(Spot.name).all()
themes = db.query(Theme).filter_by(active=True).order_by(Theme.name).all()
tranches = db.query(WindTranche).filter_by(active=True).order_by(WindTranche.min_knots).all()

if not groups or not spots or not themes or not tranches:
    st.warning(
        "Certaines listes (groupes, lieux, thématiques ou tranches de vent) sont vides. "
        "Rends-toi dans **⚙️ Configuration** pour les compléter avant de saisir une séance."
    )
    db.close()
    st.stop()

WIDGET_KEYS = [
    "saisie_date", "saisie_start", "saisie_end", "saisie_spot", "saisie_group",
    "saisie_theme", "saisie_present", "saisie_coach", "saisie_comments",
] + [f"saisie_wind_{t.id}" for t in tranches]


def _reset_form():
    for k in WIDGET_KEYS:
        st.session_state.pop(k, None)


# ---------------------------------------------------------------------------
# Informations générales
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    session_date = st.date_input("Date de la séance", value=date.today(), key="saisie_date")
    spot = st.selectbox("Lieu de navigation", spots, format_func=str, key="saisie_spot")
    group = st.selectbox("Groupe concerné", groups, format_func=str, key="saisie_group")
    theme = st.selectbox("Thématique de travail", themes, format_func=str, key="saisie_theme")
    coach_name = st.text_input("Encadrant(e)", placeholder="Nom de l'entraîneur", key="saisie_coach")

with col2:
    st.markdown("**Horaires**")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        start_time = st.time_input("Heure de début", value=time(14, 0), key="saisie_start")
    with tcol2:
        end_time = st.time_input("Heure de fin", value=time(16, 0), key="saisie_end")

    duration = compute_duration_hours(start_time, end_time)
    if duration <= 0:
        st.error("L'heure de fin doit être postérieure à l'heure de début.")
    else:
        st.metric("Durée sur l'eau", f"{duration:.2f} h")

    st.markdown("**Répartition du temps par tranche de vent**")
    st.caption("Le total doit correspondre à la durée de la séance.")
    wind_cols = st.columns(len(tranches))
    split_hours = {}
    for i, t in enumerate(tranches):
        with wind_cols[i]:
            split_hours[t.id] = st.number_input(
                t.label, min_value=0.0, max_value=12.0, value=0.0, step=0.25,
                key=f"saisie_wind_{t.id}"
            )

    total_split = sum(split_hours.values())
    remaining = round(duration - total_split, 2)
    if duration > 0:
        if abs(remaining) < 0.01:
            st.success(f"Réparti : {total_split:.2f} h / {duration:.2f} h ✅")
        elif remaining > 0:
            st.warning(f"Réparti : {total_split:.2f} h / {duration:.2f} h — il reste {remaining:.2f} h à répartir")
        else:
            st.error(f"Réparti : {total_split:.2f} h / {duration:.2f} h — dépassement de {-remaining:.2f} h")

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Athlètes présents
# ---------------------------------------------------------------------------
all_athletes = db.query(Athlete).filter_by(active=True).order_by(Athlete.last_name).all()
default_present = [a for a in all_athletes if a.group_id == group.id]

present = st.multiselect(
    "Athlètes présents",
    options=all_athletes,
    default=default_present,
    format_func=lambda a: f"{a.full_name} ({a.group.name if a.group else '—'})",
    key="saisie_present",
    help="Pré-rempli avec le groupe sélectionné — ajuste si besoin (absents, invités d'un autre groupe...)."
)

comments = st.text_area("Commentaires / observations", placeholder="Points travaillés, remarques...", key="saisie_comments")

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

if st.button("Enregistrer la séance", use_container_width=True, type="primary"):
    errors = []
    if duration <= 0:
        errors.append("L'heure de fin doit être postérieure à l'heure de début.")
    if abs(remaining) >= 0.01:
        errors.append("La répartition par tranche de vent doit correspondre exactement à la durée de la séance.")
    if not present:
        errors.append("Sélectionne au moins un athlète présent.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        new_session = TrainingSession(
            session_date=session_date,
            spot_id=spot.id,
            group_id=group.id,
            theme_id=theme.id,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration,
            comments=comments,
            coach_name=coach_name,
        )
        new_session.athletes = db.query(Athlete).filter(
            Athlete.id.in_([a.id for a in present])
        ).all()
        db.add(new_session)
        db.flush()  # pour obtenir new_session.id avant de créer les splits

        for tranche_id, hours in split_hours.items():
            if hours > 0:
                db.add(SessionWindSplit(session_id=new_session.id, wind_tranche_id=tranche_id, hours=hours))

        db.commit()

        st.success(
            f"Séance enregistrée : {group.name} — {spot.name} — {len(present)} athlète(s) — {duration:.2f} h."
        )
        db.close()
        _reset_form()
        st.rerun()

db.close()

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)
st.caption(
    "💡 Astuce : les tranches de vent, thématiques, lieux et athlètes se gèrent dans "
    "**⚙️ Configuration**. Elles sont immédiatement disponibles ici."
)
