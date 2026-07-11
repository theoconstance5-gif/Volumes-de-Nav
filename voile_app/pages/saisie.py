import streamlit as st
from datetime import date, time

from db import (
    init_db, get_db, Group, Athlete, Spot, Theme, WindTranche,
    TrainingSession, SessionWindSplit, SessionThemeSplit, compute_duration_hours
)
from style import page_header, require_coach_auth

require_coach_auth()
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
        "Rends-toi dans **Configuration** pour les compléter avant de saisir une séance."
    )
    db.close()
    st.stop()

WIDGET_KEYS = [
    "saisie_date", "saisie_start", "saisie_end", "saisie_spot", "saisie_group",
    "saisie_themes", "saisie_theme_ratio", "saisie_present", "saisie_coach", "saisie_comments",
] + [f"saisie_wind_{t.id}" for t in tranches]


def _reset_form():
    for k in WIDGET_KEYS:
        st.session_state.pop(k, None)
    st.session_state.pop("_saisie_last_group_id", None)


spot_options = {s.id: s.name for s in spots}
group_options = {g.id: g.name for g in groups}
theme_options = {t.id: t.name for t in themes}

# ---------------------------------------------------------------------------
# Informations générales
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    session_date = st.date_input("Date de la séance", value=date.today(), key="saisie_date")
    spot_id = st.selectbox(
        "Lieu de navigation", options=list(spot_options.keys()),
        format_func=lambda i: spot_options[i], key="saisie_spot",
    )
    spot = next(s for s in spots if s.id == spot_id)
    group_id = st.selectbox(
        "Groupe concerné", options=list(group_options.keys()),
        format_func=lambda i: group_options[i], key="saisie_group",
    )
    group = next(g for g in groups if g.id == group_id)

    # Si le groupe change, on réinitialise la sélection des athlètes présents
    # (les athlètes de l'ancien groupe ne sont plus des options valides).
    if st.session_state.get("_saisie_last_group_id") != group.id:
        st.session_state.pop("saisie_present", None)
        st.session_state["_saisie_last_group_id"] = group.id

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

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Thématique(s) de travail — 1 ou 2, avec curseur de répartition si 2
# ---------------------------------------------------------------------------
st.markdown("**Thématique(s) de travail**")
selected_theme_ids = st.multiselect(
    "Choisis 1 ou 2 thématiques",
    options=list(theme_options.keys()),
    format_func=lambda i: theme_options[i],
    max_selections=2,
    key="saisie_themes",
    help="Sélectionne jusqu'à 2 thématiques. Avec 2, un curseur permet de répartir le temps entre elles."
)
selected_themes = [t for t in themes if t.id in selected_theme_ids]

theme_hours = {}  # theme_id -> heures

if len(selected_themes) == 0:
    st.caption("Sélectionne au moins une thématique.")
elif len(selected_themes) == 1:
    theme_hours[selected_themes[0].id] = duration if duration > 0 else 0.0
    st.caption(f"100 % du temps sur « {selected_themes[0].name} ».")
else:
    theme_a, theme_b = selected_themes[0], selected_themes[1]
    ratio = st.slider(
        f"Répartition du temps : « {theme_a.name} » ⟷ « {theme_b.name} »",
        min_value=0, max_value=100, value=50, step=5,
        format="%d%%",
        key="saisie_theme_ratio",
    )
    hours_a = round(duration * ratio / 100, 2) if duration > 0 else 0.0
    hours_b = round(duration - hours_a, 2) if duration > 0 else 0.0
    theme_hours[theme_a.id] = hours_a
    theme_hours[theme_b.id] = hours_b
    cA, cB = st.columns(2)
    cA.metric(theme_a.name, f"{hours_a:.2f} h")
    cB.metric(theme_b.name, f"{hours_b:.2f} h")

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Répartition du temps par tranche de vent
# ---------------------------------------------------------------------------
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
# Athlètes présents — limités au groupe sélectionné
# ---------------------------------------------------------------------------
group_athletes = db.query(Athlete).filter_by(active=True, group_id=group.id).order_by(Athlete.last_name).all()
group_athlete_options = {a.id: a.full_name for a in group_athletes}

if not group_athletes:
    st.warning(f"Aucun athlète actif rattaché au groupe « {group.name} ». Ajoute-les dans **Configuration**.")
    present = []
else:
    present_ids = st.multiselect(
        "Athlètes présents",
        options=list(group_athlete_options.keys()),
        default=list(group_athlete_options.keys()),
        format_func=lambda i: group_athlete_options[i],
        key="saisie_present",
        help="Pré-rempli avec tout le groupe — décoche les absents si besoin."
    )
    present = [a for a in group_athletes if a.id in present_ids]

comments = st.text_area("Commentaires / observations", placeholder="Points travaillés, remarques...", key="saisie_comments")

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

if st.button("Enregistrer la séance", use_container_width=True, type="primary"):
    errors = []
    if duration <= 0:
        errors.append("L'heure de fin doit être postérieure à l'heure de début.")
    if abs(remaining) >= 0.01:
        errors.append("La répartition par tranche de vent doit correspondre exactement à la durée de la séance.")
    if not selected_themes:
        errors.append("Sélectionne au moins une thématique de travail.")
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

        for theme_id, hours in theme_hours.items():
            if hours > 0:
                db.add(SessionThemeSplit(session_id=new_session.id, theme_id=theme_id, hours=hours))

        db.commit()

        theme_summary = " + ".join(f"{t.name}" for t in selected_themes)
        st.success(
            f"Séance enregistrée : {group.name} — {spot.name} — {theme_summary} — "
            f"{len(present)} athlète(s) — {duration:.2f} h."
        )
        db.close()
        _reset_form()
        st.rerun()

db.close()

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)
st.caption(
    "💡 Astuce : les tranches de vent, thématiques, lieux et athlètes se gèrent dans "
    "**Configuration**. Elles sont immédiatement disponibles ici."
)
