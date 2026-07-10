import streamlit as st

from db import (
    init_db, get_db, Athlete, DebriefEpreuve, DebriefCriterion, DebriefPoint,
    DebriefResponse, DebriefRating
)
from style import page_header

init_db()

page_header("🌊", "Debrief de la journée", "À remplir par chaque équipage après chaque journée de compétition")

db = get_db()

epreuves = db.query(DebriefEpreuve).filter_by(active=True).order_by(DebriefEpreuve.name).all()
athletes = db.query(Athlete).filter_by(active=True).order_by(Athlete.last_name).all()
criteria = db.query(DebriefCriterion).filter_by(active=True).order_by(DebriefCriterion.position).all()
points = db.query(DebriefPoint).filter_by(active=True).order_by(DebriefPoint.label).all()

if not epreuves or not athletes or not criteria:
    st.warning(
        "L'épreuve du jour, les athlètes ou les critères ne sont pas encore configurés. "
        "Demande à un entraîneur de les ajouter dans **Configuration**."
    )
    db.close()
    st.stop()

with st.form("debrief_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        epreuve = st.selectbox("Épreuve", epreuves, format_func=str)
    with col2:
        jour = st.number_input("Jour du championnat", min_value=1, max_value=20, value=1, step=1)

    equipage = st.multiselect(
        "Ton équipage (toi + éventuel équipier)",
        options=athletes,
        format_func=lambda a: a.full_name,
        help="Sélectionne-toi, et ton équipier si vous naviguez à deux."
    )

    st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)
    st.markdown("**Ta journée, de 1 (pas du tout) à 5 (totalement)**")

    ratings = {}
    for c in criteria:
        ratings[c.id] = st.slider(c.label, min_value=1, max_value=5, value=3, key=f"debrief_rating_{c.id}")

    st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

    point_options = ["—"] + [str(p) for p in points]
    col3, col4 = st.columns(2)
    with col3:
        point_noir_label = st.selectbox("LE point noir principal de la journée", point_options)
    with col4:
        point_positif_label = st.selectbox("LE point positif principal de la journée", point_options)

    commentaire = st.text_area("Autre chose à ajouter ? (optionnel)", placeholder="Commentaire libre...")

    submitted = st.form_submit_button("Envoyer mon debrief", use_container_width=True, type="primary")

    if submitted:
        if not equipage:
            st.error("Sélectionne au moins un membre d'équipage (toi-même).")
        else:
            point_noir = next((p for p in points if str(p) == point_noir_label), None)
            point_positif = next((p for p in points if str(p) == point_positif_label), None)

            response = DebriefResponse(
                epreuve_id=epreuve.id,
                jour=int(jour),
                point_noir_id=point_noir.id if point_noir else None,
                point_positif_id=point_positif.id if point_positif else None,
                commentaire=commentaire,
            )
            response.athletes = db.query(Athlete).filter(
                Athlete.id.in_([a.id for a in equipage])
            ).all()
            db.add(response)
            db.flush()

            for crit_id, val in ratings.items():
                db.add(DebriefRating(response_id=response.id, criterion_id=crit_id, value=val))

            db.commit()
            st.success("Merci ! Ton debrief a bien été envoyé. 🎉")

db.close()
