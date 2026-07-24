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

tab_groupe, tab_indiv, tab_gestion = st.tabs(
    ["👥 Analyse du groupe", "🧍 Analyse individuelle", "🛠️ Gérer les debriefs"]
)

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
    st.plotly_chart(fig_radar, use_container_width=True, key="chart_radar_groupe")

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
            st.plotly_chart(fig_noir, use_container_width=True, key="chart_noir_groupe")

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
            st.plotly_chart(fig_pos, use_container_width=True, key="chart_pos_groupe")

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
        st.plotly_chart(fig_radar2, use_container_width=True, key="chart_radar_indiv")

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
            st.plotly_chart(fig_evo, use_container_width=True, key="chart_evo_indiv")

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
                st.plotly_chart(fig_indiv_noir, use_container_width=True, key="chart_noir_indiv")
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
                st.plotly_chart(fig_indiv_pos, use_container_width=True, key="chart_pos_indiv")

# ===========================================================================
# GESTION — MODIFIER / SUPPRIMER UN DEBRIEF ENREGISTRÉ
# ===========================================================================
with tab_gestion:
    st.caption(f"{len(responses)} debrief(s) enregistré(s) pour « {epreuve.name} ».")

    all_points = db.query(DebriefPoint).order_by(DebriefPoint.label).all()
    all_athletes = db.query(Athlete).order_by(Athlete.last_name).all()
    point_options = {None: "—"} | {p.id: p.label for p in all_points}

    responses_sorted = sorted(responses, key=lambda r: (r.jour, r.athletes_label))
    response_options = {
        r.id: f"{r.athletes_label} — Jour {r.jour} — envoyé le "
              f"{r.submitted_at.strftime('%d/%m/%Y %H:%M') if r.submitted_at else '?'}"
        for r in responses_sorted
    }

    selected_resp_id = st.selectbox(
        "Choisis un debrief à modifier ou supprimer",
        options=list(response_options.keys()),
        format_func=lambda i: response_options[i],
        key="gestion_select",
    )
    resp = next(r for r in responses if r.id == selected_resp_id)
    ratings_by_crit = {rt.criterion_id: rt.value for rt in resp.ratings}

    with st.form(f"edit_resp_{resp.id}"):
        c1, c2 = st.columns(2)
        with c1:
            jour_edit = st.number_input("Jour du championnat", min_value=1, max_value=20, value=resp.jour, step=1)
            athletes_edit = st.multiselect(
                "Équipage", options=[a.id for a in all_athletes],
                default=[a.id for a in resp.athletes],
                format_func=lambda i: next(a.full_name for a in all_athletes if a.id == i),
            )
        with c2:
            noir_edit = st.selectbox(
                "Point noir", options=list(point_options.keys()),
                index=list(point_options.keys()).index(resp.point_noir_id) if resp.point_noir_id in point_options else 0,
                format_func=lambda i: point_options[i],
            )
            positif_edit = st.selectbox(
                "Point positif", options=list(point_options.keys()),
                index=list(point_options.keys()).index(resp.point_positif_id) if resp.point_positif_id in point_options else 0,
                format_func=lambda i: point_options[i],
            )

        st.markdown("**Notes par critère**")
        new_ratings = {}
        for crit in criteria:
            new_ratings[crit.id] = st.slider(
                crit.label, min_value=1, max_value=5,
                value=ratings_by_crit.get(crit.id, 3), key=f"edit_rating_{resp.id}_{crit.id}",
            )

        commentaire_edit = st.text_area("Commentaire libre", value=resp.commentaire or "")

        if st.form_submit_button("💾 Enregistrer les modifications", type="primary", use_container_width=True):
            if not athletes_edit:
                st.error("Sélectionne au moins un membre d'équipage.")
            else:
                resp.jour = int(jour_edit)
                resp.point_noir_id = noir_edit
                resp.point_positif_id = positif_edit
                resp.commentaire = commentaire_edit
                resp.athletes = [a for a in all_athletes if a.id in athletes_edit]
                for rt in resp.ratings:
                    if rt.criterion_id in new_ratings:
                        rt.value = new_ratings[rt.criterion_id]
                db.commit()
                st.success("Debrief mis à jour.")
                st.rerun()

    st.html("<hr>")
    st.markdown("**Zone de suppression**")
    confirm_delete = st.checkbox(
        "Je confirme vouloir supprimer définitivement ce debrief (irréversible)",
        key=f"confirm_del_{resp.id}",
    )
    if st.button("🗑️ Supprimer ce debrief", disabled=not confirm_delete):
        db.delete(resp)
        db.commit()
        st.success("Debrief supprimé.")
        st.rerun()

db.close()
