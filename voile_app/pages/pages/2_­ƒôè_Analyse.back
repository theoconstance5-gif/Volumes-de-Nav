import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from db import (
    init_db, get_db, Group, Athlete, Spot, Theme, WindTranche, TrainingSession
)
from style import inject_css, page_header, sidebar_logo, PALETTE, CHART_COLORS

st.set_page_config(page_title="Analyse — La Vague Normande Sport", page_icon="assets/logo_icon.png", layout="wide")
inject_css()
sidebar_logo()
init_db()

page_header("📊", "Analyse des volumes d'entraînement", "Filtre, compare et explore les données de la saison")

db = get_db()

groups = db.query(Group).order_by(Group.name).all()
athletes = db.query(Athlete).order_by(Athlete.last_name).all()
themes = db.query(Theme).order_by(Theme.name).all()
tranches = db.query(WindTranche).order_by(WindTranche.min_knots).all()

sessions = db.query(TrainingSession).all()

if not sessions:
    st.info("Aucune séance enregistrée pour l'instant. Rends-toi dans **📝 Saisie** pour en ajouter.")
    st.stop()

# ---------------------------------------------------------------------------
# Construction du dataframe "détail" :
# une ligne = un athlète présent, pour une tranche de vent d'une séance donnée
# (le temps de chaque séance est réparti entre 1 à plusieurs tranches de vent ;
#  cette répartition s'applique à tous les athlètes présents ce jour-là).
# ---------------------------------------------------------------------------
rows = []
for s in sessions:
    if not s.wind_splits:
        continue
    for a in s.athletes:
        for split in s.wind_splits:
            rows.append({
                "session_id": s.id,
                "date": s.session_date,
                "groupe": s.group.name if s.group else "—",
                "athlete": a.full_name,
                "athlete_id": a.id,
                "lieu": s.spot.name if s.spot else "—",
                "thematique": s.theme.name if s.theme else "—",
                "tranche_vent": split.wind_tranche.label if split.wind_tranche else "Non classé",
                "duree_h": split.hours,
                "encadrant": s.coach_name,
                "heure_debut": s.start_time.strftime("%H:%M") if s.start_time else "",
                "heure_fin": s.end_time.strftime("%H:%M") if s.end_time else "",
            })

df = pd.DataFrame(rows)

if df.empty:
    st.warning(
        "Les séances enregistrées n'ont pas de répartition par tranche de vent renseignée. "
        "Vérifie la saisie."
    )
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# ---------------------------------------------------------------------------
# Filtres (barre latérale)
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🔎 Filtres")

min_date, max_date = df["date"].min().date(), df["date"].max().date()
period = st.sidebar.date_input(
    "Période",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(period, tuple) and len(period) == 2:
    start_date, end_date = period
else:
    start_date, end_date = min_date, max_date

compare_mode = st.sidebar.radio("Comparer par", ["Groupes", "Athlètes"], horizontal=True)

if compare_mode == "Groupes":
    group_names = sorted(df["groupe"].unique())
    selected_entities = st.sidebar.multiselect("Groupes à comparer", group_names, default=group_names)
else:
    athlete_names = sorted(df["athlete"].unique())
    selected_entities = st.sidebar.multiselect(
        "Athlètes à comparer", athlete_names,
        default=athlete_names[: min(6, len(athlete_names))]
    )

theme_filter = st.sidebar.multiselect("Thématiques", sorted(df["thematique"].unique()))
tranche_filter = st.sidebar.multiselect("Tranches de vent", sorted(df["tranche_vent"].unique()))
spot_filter = st.sidebar.multiselect("Lieux", sorted(df["lieu"].unique()))

# ---------------------------------------------------------------------------
# Application des filtres
# ---------------------------------------------------------------------------
mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))

if selected_entities:
    col = "groupe" if compare_mode == "Groupes" else "athlete"
    mask &= df[col].isin(selected_entities)
if theme_filter:
    mask &= df["thematique"].isin(theme_filter)
if tranche_filter:
    mask &= df["tranche_vent"].isin(tranche_filter)
if spot_filter:
    mask &= df["lieu"].isin(spot_filter)

fdf = df[mask].copy()

if fdf.empty:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
    st.stop()

entity_col = "groupe" if compare_mode == "Groupes" else "athlete"

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Volume total", f"{fdf['duree_h'].sum():.1f} h")
k2.metric("Séances (uniques)", f"{fdf['session_id'].nunique()}")
k3.metric("Athlètes actifs", f"{fdf['athlete_id'].nunique()}")
dominant_tranche = fdf.groupby("tranche_vent")["duree_h"].sum().idxmax()
k4.metric("Tranche de vent dominante", dominant_tranche)

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Comparaison volume par entité
# ---------------------------------------------------------------------------
st.subheader(f"Volume total par {'groupe' if compare_mode == 'Groupes' else 'athlète'}")

agg = fdf.groupby(entity_col)["duree_h"].sum().sort_values(ascending=True).reset_index()
fig_bar = px.bar(
    agg, x="duree_h", y=entity_col, orientation="h",
    text="duree_h", color_discrete_sequence=[PALETTE["coral"]],
    labels={"duree_h": "Volume (heures)", entity_col: ""},
)
fig_bar.update_traces(texttemplate="%{text:.1f} h", textposition="outside")
fig_bar.update_layout(plot_bgcolor="white", paper_bgcolor="white", showlegend=False, height=max(300, 40 * len(agg)))
st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------------------------
# Évolution temporelle
# ---------------------------------------------------------------------------
st.subheader("Évolution du volume dans le temps")
granularity = st.radio("Granularité", ["Semaine", "Mois"], horizontal=True, label_visibility="collapsed")
freq = "W" if granularity == "Semaine" else "M"

time_agg = (
    fdf.groupby([pd.Grouper(key="date", freq=freq), entity_col])["duree_h"]
    .sum()
    .reset_index()
)
fig_line = px.line(
    time_agg, x="date", y="duree_h", color=entity_col, markers=True,
    color_discrete_sequence=CHART_COLORS,
    labels={"duree_h": "Volume (heures)", "date": "", entity_col: ""},
)
fig_line.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
st.plotly_chart(fig_line, use_container_width=True)

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Analyse par tranche de vent / thématique
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Volume par tranche de vent")
    wind_agg = fdf.groupby("tranche_vent")["duree_h"].sum().reset_index()
    fig_wind = px.pie(
        wind_agg, names="tranche_vent", values="duree_h", hole=0.55,
        color_discrete_sequence=CHART_COLORS,
    )
    fig_wind.update_traces(textinfo="percent+label")
    fig_wind.update_layout(showlegend=False)
    st.plotly_chart(fig_wind, use_container_width=True)

with c2:
    st.subheader("Volume par thématique")
    theme_agg = fdf.groupby("thematique")["duree_h"].sum().reset_index().sort_values("duree_h")
    fig_theme = px.bar(
        theme_agg, x="duree_h", y="thematique", orientation="h",
        color_discrete_sequence=[PALETTE["black"]],
        labels={"duree_h": "Volume (heures)", "thematique": ""},
    )
    fig_theme.update_layout(plot_bgcolor="white", paper_bgcolor="white", height=max(300, 35 * len(theme_agg)))
    st.plotly_chart(fig_theme, use_container_width=True)

# ---------------------------------------------------------------------------
# Croisement entité x tranche de vent (heatmap) — utile pour comparer profils
# ---------------------------------------------------------------------------
st.subheader(f"Répartition croisée : {'groupe' if compare_mode == 'Groupes' else 'athlète'} × tranche de vent")
cross = fdf.pivot_table(index=entity_col, columns="tranche_vent", values="duree_h", aggfunc="sum", fill_value=0)
fig_heat = go.Figure(data=go.Heatmap(
    z=cross.values, x=cross.columns, y=cross.index,
    colorscale=[[0, "#FFFFFF"], [1, PALETTE["coral"]]],
    text=cross.values.round(1), texttemplate="%{text}",
    colorbar=dict(title="heures"),
))
fig_heat.update_layout(height=max(300, 40 * len(cross)), paper_bgcolor="white")
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Détail / export
# ---------------------------------------------------------------------------
with st.expander("📋 Voir le détail des séances filtrées"):
    detail_cols = [
        "date", "groupe", "athlete", "lieu", "thematique",
        "heure_debut", "heure_fin", "tranche_vent", "duree_h", "encadrant"
    ]
    display_df = fdf[detail_cols].sort_values("date", ascending=False).rename(columns={
        "date": "Date", "groupe": "Groupe", "athlete": "Athlète", "lieu": "Lieu",
        "thematique": "Thématique", "heure_debut": "Début", "heure_fin": "Fin",
        "tranche_vent": "Tranche de vent", "duree_h": "Durée (h)", "encadrant": "Encadrant",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Exporter en CSV",
        display_df.to_csv(index=False).encode("utf-8"),
        file_name=f"suivi_voile_{start_date}_{end_date}.csv",
        mime="text/csv",
    )

db.close()
