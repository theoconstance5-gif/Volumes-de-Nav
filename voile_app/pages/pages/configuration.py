import streamlit as st
import pandas as pd

from db import (
    init_db, get_db, Group, Athlete, Spot, Theme, WindTranche,
    DebriefEpreuve, DebriefCriterion, DebriefPoint
)
from style import page_header, require_coach_auth

require_coach_auth()
init_db()

page_header("⚙️", "Configuration des listes", "Gère les référentiels utilisés dans la saisie et l'analyse")

db = get_db()

tab_groups, tab_athletes, tab_spots, tab_themes, tab_wind, tab_epreuves, tab_criteria, tab_points = st.tabs(
    ["👥 Groupes", "🧍 Athlètes", "📍 Lieux", "🎯 Thématiques", "💨 Tranches de vent",
     "🏆 Épreuves", "📋 Critères debrief", "🔍 Points debrief"]
)

# ---------------------------------------------------------------------------
# Groupes
# ---------------------------------------------------------------------------
with tab_groups:
    st.subheader("Groupes")
    groups = db.query(Group).order_by(Group.name).all()

    with st.form("add_group", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Nom du nouveau groupe")
        submitted = c2.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted and name.strip():
            if db.query(Group).filter_by(name=name.strip()).first():
                st.error("Ce groupe existe déjà.")
            else:
                db.add(Group(name=name.strip()))
                db.commit()
                st.success(f"Groupe « {name} » ajouté.")
                st.rerun()

    if groups:
        for g in groups:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(g.name)
            active = c2.toggle("Actif", value=g.active, key=f"group_active_{g.id}")
            if active != g.active:
                g.active = active
                db.commit()
                st.rerun()
            if c3.button("🗑️ Supprimer", key=f"del_group_{g.id}"):
                if g.athletes:
                    st.error("Impossible : des athlètes sont rattachés à ce groupe.")
                else:
                    db.delete(g)
                    db.commit()
                    st.rerun()
    else:
        st.caption("Aucun groupe pour l'instant.")

# ---------------------------------------------------------------------------
# Athlètes
# ---------------------------------------------------------------------------
with tab_athletes:
    st.subheader("Athlètes")
    groups = db.query(Group).filter_by(active=True).order_by(Group.name).all()

    if not groups:
        st.warning("Crée d'abord au moins un groupe (onglet Groupes).")
    else:
        with st.form("add_athlete", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            first_name = c1.text_input("Prénom")
            last_name = c2.text_input("Nom")
            group = c3.selectbox("Groupe", groups, format_func=str)
            submitted = c4.form_submit_button("➕ Ajouter", use_container_width=True)
            if submitted and first_name.strip() and last_name.strip():
                db.add(Athlete(first_name=first_name.strip(), last_name=last_name.strip(), group_id=group.id))
                db.commit()
                st.success(f"Athlète « {first_name} {last_name} » ajouté(e).")
                st.rerun()

        athletes = db.query(Athlete).order_by(Athlete.last_name).all()
        if athletes:
            for a in athletes:
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                c1.write(a.full_name)
                current_group = c2.selectbox(
                    "Groupe", groups, index=next((i for i, g in enumerate(groups) if g.id == a.group_id), 0),
                    key=f"athlete_group_{a.id}", format_func=str, label_visibility="collapsed"
                )
                if current_group.id != a.group_id:
                    a.group_id = current_group.id
                    db.commit()
                    st.rerun()
                active = c3.toggle("Actif", value=a.active, key=f"athlete_active_{a.id}")
                if active != a.active:
                    a.active = active
                    db.commit()
                    st.rerun()
                if c4.button("🗑️", key=f"del_athlete_{a.id}"):
                    db.delete(a)
                    db.commit()
                    st.rerun()
        else:
            st.caption("Aucun athlète pour l'instant.")

# ---------------------------------------------------------------------------
# Lieux
# ---------------------------------------------------------------------------
with tab_spots:
    st.subheader("Lieux de navigation")
    spots = db.query(Spot).order_by(Spot.name).all()

    with st.form("add_spot", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Nom du lieu")
        submitted = c2.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted and name.strip():
            if db.query(Spot).filter_by(name=name.strip()).first():
                st.error("Ce lieu existe déjà.")
            else:
                db.add(Spot(name=name.strip()))
                db.commit()
                st.success(f"Lieu « {name} » ajouté.")
                st.rerun()

    for s in spots:
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(s.name)
        active = c2.toggle("Actif", value=s.active, key=f"spot_active_{s.id}")
        if active != s.active:
            s.active = active
            db.commit()
            st.rerun()
        if c3.button("🗑️ Supprimer", key=f"del_spot_{s.id}"):
            db.delete(s)
            db.commit()
            st.rerun()

# ---------------------------------------------------------------------------
# Thématiques
# ---------------------------------------------------------------------------
with tab_themes:
    st.subheader("Thématiques de travail")
    themes = db.query(Theme).order_by(Theme.name).all()

    with st.form("add_theme", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Nom de la thématique")
        submitted = c2.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted and name.strip():
            if db.query(Theme).filter_by(name=name.strip()).first():
                st.error("Cette thématique existe déjà.")
            else:
                db.add(Theme(name=name.strip()))
                db.commit()
                st.success(f"Thématique « {name} » ajoutée.")
                st.rerun()

    for t in themes:
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(t.name)
        active = c2.toggle("Actif", value=t.active, key=f"theme_active_{t.id}")
        if active != t.active:
            t.active = active
            db.commit()
            st.rerun()
        if c3.button("🗑️ Supprimer", key=f"del_theme_{t.id}"):
            db.delete(t)
            db.commit()
            st.rerun()

# ---------------------------------------------------------------------------
# Tranches de vent
# ---------------------------------------------------------------------------
with tab_wind:
    st.subheader("Tranches de vent")
    st.caption(
        "Définis les tranches de vent (en nœuds) proposées lors de la saisie : le temps de "
        "chaque séance est réparti par l'entraîneur entre ces tranches (ex : 0-10 / 10-17 / +17 nds)."
    )
    tranches = db.query(WindTranche).order_by(WindTranche.min_knots).all()

    with st.form("add_tranche", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        label = c1.text_input("Libellé", placeholder="ex : Médium")
        min_k = c2.number_input("Min (nds)", min_value=0.0, max_value=60.0, value=0.0, step=1.0)
        max_k = c3.number_input("Max (nds)", min_value=0.0, max_value=60.0, value=10.0, step=1.0)
        submitted = c4.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted and label.strip():
            if max_k <= min_k:
                st.error("Le max doit être supérieur au min.")
            else:
                db.add(WindTranche(label=label.strip(), min_knots=min_k, max_knots=max_k))
                db.commit()
                st.success(f"Tranche « {label} » ajoutée.")
                st.rerun()

    for t in tranches:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
        c1.write(t.label)
        c2.write(f"{t.min_knots:g} nds")
        c3.write(f"{t.max_knots:g} nds")
        active = c4.toggle("Actif", value=t.active, key=f"tranche_active_{t.id}")
        if active != t.active:
            t.active = active
            db.commit()
            st.rerun()
        if c5.button("🗑️", key=f"del_tranche_{t.id}"):
            db.delete(t)
            db.commit()
            st.rerun()

# ---------------------------------------------------------------------------
# Épreuves (debrief)
# ---------------------------------------------------------------------------
with tab_epreuves:
    st.subheader("Épreuves")
    st.caption("Compétitions / lieux d'épreuve proposés dans le formulaire de debrief.")
    epreuves = db.query(DebriefEpreuve).order_by(DebriefEpreuve.name).all()

    with st.form("add_epreuve", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Nom de l'épreuve", placeholder="ex : Palamos")
        submitted = c2.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted and name.strip():
            if db.query(DebriefEpreuve).filter_by(name=name.strip()).first():
                st.error("Cette épreuve existe déjà.")
            else:
                db.add(DebriefEpreuve(name=name.strip()))
                db.commit()
                st.success(f"Épreuve « {name} » ajoutée.")
                st.rerun()

    for e in epreuves:
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(e.name)
        active = c2.toggle("Active", value=e.active, key=f"epreuve_active_{e.id}")
        if active != e.active:
            e.active = active
            db.commit()
            st.rerun()
        if c3.button("🗑️ Supprimer", key=f"del_epreuve_{e.id}"):
            db.delete(e)
            db.commit()
            st.rerun()

# ---------------------------------------------------------------------------
# Critères de debrief
# ---------------------------------------------------------------------------
with tab_criteria:
    st.subheader("Critères notés dans le debrief")
    st.caption("Chaque athlète note ces critères de 1 à 5 après chaque journée. L'ordre ci-dessous est celui du formulaire.")
    criteria = db.query(DebriefCriterion).order_by(DebriefCriterion.position).all()

    with st.form("add_criterion", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        label = c1.text_input("Libellé du critère", placeholder="ex : J'ai fait un bon départ")
        submitted = c2.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted and label.strip():
            if db.query(DebriefCriterion).filter_by(label=label.strip()).first():
                st.error("Ce critère existe déjà.")
            else:
                max_pos = db.query(DebriefCriterion).count()
                db.add(DebriefCriterion(label=label.strip(), position=max_pos))
                db.commit()
                st.success(f"Critère « {label} » ajouté.")
                st.rerun()

    for c in criteria:
        c1, c2, c3 = st.columns([4, 1, 1])
        c1.write(c.label)
        active = c2.toggle("Actif", value=c.active, key=f"criterion_active_{c.id}")
        if active != c.active:
            c.active = active
            db.commit()
            st.rerun()
        if c3.button("🗑️", key=f"del_criterion_{c.id}"):
            db.delete(c)
            db.commit()
            st.rerun()

# ---------------------------------------------------------------------------
# Points de debrief (point noir / point positif)
# ---------------------------------------------------------------------------
with tab_points:
    st.subheader("Points techniques (point noir / point positif)")
    st.caption("Liste proposée dans le debrief pour désigner LE point noir et LE point positif de la journée.")
    points = db.query(DebriefPoint).order_by(DebriefPoint.label).all()

    with st.form("add_point", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        label = c1.text_input("Libellé du point", placeholder="ex : Le placement au départ")
        submitted = c2.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted and label.strip():
            if db.query(DebriefPoint).filter_by(label=label.strip()).first():
                st.error("Ce point existe déjà.")
            else:
                db.add(DebriefPoint(label=label.strip()))
                db.commit()
                st.success(f"Point « {label} » ajouté.")
                st.rerun()

    for p in points:
        c1, c2, c3 = st.columns([4, 1, 1])
        c1.write(p.label)
        active = c2.toggle("Actif", value=p.active, key=f"point_active_{p.id}")
        if active != p.active:
            p.active = active
            db.commit()
            st.rerun()
        if c3.button("🗑️", key=f"del_point_{p.id}"):
            db.delete(p)
            db.commit()
            st.rerun()

db.close()
