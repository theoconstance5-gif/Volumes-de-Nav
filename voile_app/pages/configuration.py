import streamlit as st
import pandas as pd

from db import init_db, get_db, Group, Athlete, Spot, Theme, WindTranche
from style import page_header

init_db()

page_header("⚙️", "Configuration des listes", "Gère les référentiels utilisés dans la saisie et l'analyse")

db = get_db()

tab_groups, tab_athletes, tab_spots, tab_themes, tab_wind = st.tabs(
    ["👥 Groupes", "🧍 Athlètes", "📍 Lieux", "🎯 Thématiques", "💨 Tranches de vent"]
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

db.close()
