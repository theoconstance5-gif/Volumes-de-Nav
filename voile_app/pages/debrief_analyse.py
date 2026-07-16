import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from db import (
    init_db, get_db, Athlete, DebriefEpreuve, DebriefCriterion, DebriefPoint,
    DebriefResponse, DebriefRating
)
from style import page_header, require_coach_auth, PALETTE, CHART_COLORS

require_coach_auth()
init_db()

page_header("🌊", "Analyse du debrief", "Profil du groupe et comparaison individuelle")

db = get_db()

epreuves = db.query(DebriefEpreuve).order_by(DebriefEpreuve.name).all()
criteria = db.query(DebriefCriterion).filter_by(active=True).order_by(DebriefCriterion.position).all()

if not epreuves:
    st.info("Aucune épreuve configurée pour l'instant. Ajoute-en dans **Configuration**.")
    st.stop()

epreuve_options = {e.id: e.name for e in epreuves}
epreuve_id = st.selectbox(
    "Épreuve à analyser", options=list(epreuve_options.keys()),
    format_func=lambda i: epreuve_options[i],
)
epreuve = next(e for e in epreuves if e.id == epreuve_id)

responses = (
    db.query(DebriefResponse)
    .filter(DebriefResponse.epreuve_id == epreuve.id)
    .all()
)

if not responses:
    st.info(f"Aucune réponse de debrief pour « {epreuve.name} » pour l'instant.")
    db.close()
    st.stop()

# ---------------------------------------------------------------------------
# Construction des dataframes
# ---------------------------------------------------------------------------
rating_rows = []
for r in responses:
    for rt in r.ratings:
        rating_rows.append({
            "response_id": r.id, "jour": r.jour, "athletes": r.athletes_label,
            "critere": rt.criterion.label, "valeur": rt.value,
        })
df_ratings = pd.DataFrame(rating_rows)

point_rows = []
for r in responses:
    if r.point_noir:
        point_rows.append({"response_id": r.id, "athletes": r.athletes_label, "type": "Point noir", "point": r.point_noir.label})
    if r.point_positif:
        point_rows.append({"response_id": r.id, "athletes": r.athletes_label, "type": "Point positif", "point": r.point_positif.label})
df_points = pd.DataFrame(point_rows)

criterion_labels = [c.label for c in criteria]

tab_groupe, tab_indiv = st.tabs(["👥 Analyse du groupe", "🧍 Analyse individuelle"])

# ===========================================================================
# ANALYSE DU GROUPE
# ===========================================================================
with tab_groupe:
    st.metric("Nombre de réponses", len(responses))

    group_avg = df_ratings.groupby("critere")["valeur"].mean().reindex(criterion_labels).round(2)

    st.subheader("Profil moyen du groupe")
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=list(group_avg.values) + [group_avg.values[0]],
        theta=criterion_labels + [criterion_labels[0]],
        fill="toself", name="Groupe",
        line_color=PALETTE["coral"],
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=False, height=500,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Points d'attention")
        noirs = df_points[df_points["type"] == "Point noir"]["point"].value_counts()
        if noirs.empty:
            st.caption("Aucun point noir renseigné.")
        else:
            fig_noir = px.pie(
                names=noirs.index, values=noirs.values, hole=0.4,
                color_discrete_sequence=CHART_COLORS,
            )
            fig_noir.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_noir, use_container_width=True)

    with c2:
        st.subheader("Points positifs")
        positifs = df_points[df_points["type"] == "Point positif"]["point"].value_counts()
        if positifs.empty:
            st.caption("Aucun point positif renseigné.")
        else:
            fig_pos = px.pie(
                names=positifs.index, values=positifs.values, hole=0.4,
                color_discrete_sequence=CHART_COLORS,
            )
            fig_pos.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_pos, use_container_width=True)

# ===========================================================================
# ANALYSE INDIVIDUELLE
# ===========================================================================
with tab_indiv:
    athlete_names = sorted(df_ratings["athletes"].unique())
    if not athlete_names:
        st.caption("Pas de données individuelles pour cette épreuve.")
    else:
        selected_name = st.selectbox("Équipage / athlète", athlete_names)

        indiv_ratings = df_ratings[df_ratings["athletes"] == selected_name]
        indiv_avg = indiv_ratings.groupby("critere")["valeur"].mean().reindex(criterion_labels).round(2)

        st.subheader(f"Profil : {selected_name} vs Groupe")
        fig_radar2 = go.Figure()
        fig_radar2.add_trace(go.Scatterpolar(
            r=list(group_avg.values) + [group_avg.values[0]],
            theta=criterion_labels + [criterion_labels[0]],
            fill="toself", name="Groupe", line_color=PALETTE["black"], opacity=0.6,
        ))
        fig_radar2.add_trace(go.Scatterpolar(
            r=list(indiv_avg.values) + [indiv_avg.values[0]],
            theta=criterion_labels + [criterion_labels[0]],
            fill="toself", name=selected_name, line_color=PALETTE["coral"],
        ))
        fig_radar2.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True, height=500,
        )
        st.plotly_chart(fig_radar2, use_container_width=True)

        st.subheader("Évolution jour par jour")
        evo = (
            indiv_ratings.groupby(["jour", "critere"])["valeur"].mean().reset_index()
        )
        if evo["jour"].nunique() < 2:
            st.caption("Il faut au moins 2 jours de données pour tracer une évolution.")
        else:
            fig_evo = px.line(
                evo, x="jour", y="valeur", color="critere", markers=True,
                color_discrete_sequence=CHART_COLORS,
                labels={"jour": "Jour du championnat", "valeur": "Note (1-5)", "critere": ""},
            )
            fig_evo.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
            st.plotly_chart(fig_evo, use_container_width=True)

        st.subheader(f"Points noirs / positifs — {selected_name}")
        indiv_points = df_points[df_points["athletes"] == selected_name]
        ci1, ci2 = st.columns(2)
        with ci1:
            st.markdown("**Points d'attention**")
            indiv_noirs = indiv_points[indiv_points["type"] == "Point noir"]["point"].value_counts()
            if indiv_noirs.empty:
                st.caption("Aucun point noir renseigné pour cet athlète.")
            else:
                fig_indiv_noir = px.pie(
                    names=indiv_noirs.index, values=indiv_noirs.values, hole=0.4,
                    color_discrete_sequence=CHART_COLORS,
                )
                fig_indiv_noir.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_indiv_noir, use_container_width=True)
        with ci2:
            st.markdown("**Points positifs**")
            indiv_positifs = indiv_points[indiv_points["type"] == "Point positif"]["point"].value_counts()
            if indiv_positifs.empty:
                st.caption("Aucun point positif renseigné pour cet athlète.")
            else:
                fig_indiv_pos = px.pie(
                    names=indiv_positifs.index, values=indiv_positifs.values, hole=0.4,
                    color_discrete_sequence=CHART_COLORS,
                )
                fig_indiv_pos.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_indiv_pos, use_container_width=True)

db.close()
