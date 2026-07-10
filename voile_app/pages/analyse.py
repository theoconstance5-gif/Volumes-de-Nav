import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from db import (
    init_db, get_db, Group, Athlete, Spot, Theme, WindTranche, TrainingSession
)
from style import page_header, require_coach_auth, PALETTE, CHART_COLORS

require_coach_auth()
init_db()

page_header("📊", "Analyse des volumes d'entraînement", "Filtre, compare et explore les données de la saison")

db = get_db()

sessions = db.query(TrainingSession).all()

if not sessions:
    st.info("Aucune séance enregistrée pour l'instant. Rends-toi dans **Saisie** pour en ajouter.")
    st.stop()

# ---------------------------------------------------------------------------
# Construction de 4 dataframes "détail", tous indexés par session_id :
#  - df_base  : 1 ligne = 1 athlète présent à 1 séance (durée totale de la séance)
#  - df_theme : 1 ligne = 1 athlète x 1 split de thématique (1 ou 2 par séance)
#  - df_wind  : 1 ligne = 1 athlète x 1 split de tranche de vent
#  - df_cross : 1 ligne = 1 athlète x 1 (thématique, tranche de vent) estimé
# On sépare thème et vent car ce sont deux répartitions indépendantes du même
# temps total (pas une grille croisée) : les combiner dans une seule ligne
# créerait un double comptage du volume. df_cross donne malgré tout une
# estimation croisée thématique x vent, en répartissant chaque split de
# thématique au prorata des tranches de vent de la séance (hypothèse : le
# mix de conditions de vent est le même quelle que soit la thématique
# travaillée pendant la séance).
# ---------------------------------------------------------------------------
base_rows, theme_rows, wind_rows, cross_rows = [], [], [], []

for s in sessions:
    if not s.wind_splits or not s.theme_splits:
        continue
    common = {
        "session_id": s.id,
        "date": s.session_date,
        "groupe": s.group.name if s.group else "—",
        "lieu": s.spot.name if s.spot else "—",
        "encadrant": s.coach_name,
        "heure_debut": s.start_time.strftime("%H:%M") if s.start_time else "",
        "heure_fin": s.end_time.strftime("%H:%M") if s.end_time else "",
    }
    for a in s.athletes:
        row_common = {**common, "athlete": a.full_name, "athlete_id": a.id}
        base_rows.append({**row_common, "duree_h": s.duration_hours})
        for ts in s.theme_splits:
            theme_rows.append({**row_common, "thematique": ts.theme.name, "duree_h": ts.hours})
        for ws in s.wind_splits:
            wind_rows.append({**row_common, "tranche_vent": ws.wind_tranche.label, "duree_h": ws.hours})
        if s.duration_hours > 0:
            for ts in s.theme_splits:
                for ws in s.wind_splits:
                    est_hours = ts.hours * ws.hours / s.duration_hours
                    cross_rows.append({
                        **row_common, "thematique": ts.theme.name,
                        "tranche_vent": ws.wind_tranche.label, "duree_h": est_hours,
                    })

df_base = pd.DataFrame(base_rows)
df_theme = pd.DataFrame(theme_rows)
df_wind = pd.DataFrame(wind_rows)
df_cross = pd.DataFrame(cross_rows)

if df_base.empty:
    st.warning(
        "Les séances enregistrées n'ont pas de répartition (thématique et/ou vent) renseignée. "
        "Vérifie la saisie."
    )
    st.stop()

for d in (df_base, df_theme, df_wind, df_cross):
    d["date"] = pd.to_datetime(d["date"])

# ---------------------------------------------------------------------------
# Filtres (barre latérale)
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🔎 Filtres")

min_date, max_date = df_base["date"].min().date(), df_base["date"].max().date()
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
entity_col = "groupe" if compare_mode == "Groupes" else "athlete"

if compare_mode == "Groupes":
    group_names = sorted(df_base["groupe"].unique())
    selected_entities = st.sidebar.multiselect("Groupes à comparer", group_names, default=group_names)
else:
    athlete_names = sorted(df_base["athlete"].unique())
    selected_entities = st.sidebar.multiselect(
        "Athlètes à comparer", athlete_names,
        default=athlete_names[: min(6, len(athlete_names))]
    )

theme_filter = st.sidebar.multiselect("Thématiques", sorted(df_theme["thematique"].unique()))
tranche_filter = st.sidebar.multiselect("Tranches de vent", sorted(df_wind["tranche_vent"].unique()))
spot_filter = st.sidebar.multiselect("Lieux", sorted(df_base["lieu"].unique()))


def _base_mask(d):
    m = (d["date"] >= pd.Timestamp(start_date)) & (d["date"] <= pd.Timestamp(end_date))
    if selected_entities:
        m &= d[entity_col].isin(selected_entities)
    if spot_filter:
        m &= d["lieu"].isin(spot_filter)
    return m


fdf_base_all = df_base[_base_mask(df_base)]
fdf_theme_all = df_theme[_base_mask(df_theme)]
fdf_wind_all = df_wind[_base_mask(df_wind)]
fdf_cross_all = df_cross[_base_mask(df_cross)]

allowed_ids = set(fdf_base_all["session_id"])
if theme_filter:
    allowed_ids &= set(fdf_theme_all.loc[fdf_theme_all["thematique"].isin(theme_filter), "session_id"])
if tranche_filter:
    allowed_ids &= set(fdf_wind_all.loc[fdf_wind_all["tranche_vent"].isin(tranche_filter), "session_id"])

fdf_base = fdf_base_all[fdf_base_all["session_id"].isin(allowed_ids)].copy()
fdf_theme = fdf_theme_all[fdf_theme_all["session_id"].isin(allowed_ids)].copy()
fdf_wind = fdf_wind_all[fdf_wind_all["session_id"].isin(allowed_ids)].copy()
fdf_cross = fdf_cross_all[fdf_cross_all["session_id"].isin(allowed_ids)].copy()

if fdf_base.empty:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Volume total", f"{fdf_base['duree_h'].sum():.1f} h")
k2.metric("Séances (uniques)", f"{fdf_base['session_id'].nunique()}")
k3.metric("Athlètes actifs", f"{fdf_base['athlete_id'].nunique()}")
dominant_tranche = fdf_wind.groupby("tranche_vent")["duree_h"].sum().idxmax() if not fdf_wind.empty else "—"
k4.metric("Tranche de vent dominante", dominant_tranche)

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Comparaison volume par entité
# ---------------------------------------------------------------------------
st.subheader(f"Volume total par {'groupe' if compare_mode == 'Groupes' else 'athlète'}")

agg = fdf_base.groupby(entity_col)["duree_h"].sum().sort_values(ascending=True).reset_index()
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
    fdf_base.groupby([pd.Grouper(key="date", freq=freq), entity_col])["duree_h"]
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
    if fdf_wind.empty:
        st.caption("Pas de données pour les filtres actuels.")
    else:
        wind_agg = fdf_wind.groupby("tranche_vent")["duree_h"].sum().reset_index()
        fig_wind = px.pie(
            wind_agg, names="tranche_vent", values="duree_h", hole=0.55,
            color_discrete_sequence=CHART_COLORS,
        )
        fig_wind.update_traces(textinfo="percent+label")
        fig_wind.update_layout(showlegend=False)
        st.plotly_chart(fig_wind, use_container_width=True)

with c2:
    st.subheader("Volume par thématique")
    if fdf_theme.empty:
        st.caption("Pas de données pour les filtres actuels.")
    else:
        theme_agg = fdf_theme.groupby("thematique")["duree_h"].sum().reset_index().sort_values("duree_h")
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
if fdf_wind.empty:
    st.caption("Pas de données pour les filtres actuels.")
else:
    cross = fdf_wind.pivot_table(index=entity_col, columns="tranche_vent", values="duree_h", aggfunc="sum", fill_value=0)
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
# Thématiques travaillées en fonction de la force du vent
# ---------------------------------------------------------------------------
st.subheader("Thématiques travaillées par tranche de vent")
st.caption(
    "Estimation : le temps de chaque thématique est réparti au prorata des tranches de vent "
    "de la séance (on suppose un mix de conditions homogène sur toute la séance)."
)
if fdf_cross.empty:
    st.caption("Pas de données pour les filtres actuels.")
else:
    cross_theme_wind = fdf_cross.pivot_table(
        index="thematique", columns="tranche_vent", values="duree_h", aggfunc="sum", fill_value=0
    )
    fig_cross = go.Figure(data=go.Heatmap(
        z=cross_theme_wind.values, x=cross_theme_wind.columns, y=cross_theme_wind.index,
        colorscale=[[0, "#FFFFFF"], [1, PALETTE["black"]]],
        text=cross_theme_wind.values.round(1), texttemplate="%{text}",
        colorbar=dict(title="heures (est.)"),
    ))
    fig_cross.update_layout(height=max(300, 40 * len(cross_theme_wind)), paper_bgcolor="white")
    st.plotly_chart(fig_cross, use_container_width=True)

    # Vue alternative en barres empilées : répartition du vent pour chaque thématique
    fig_cross_bar = px.bar(
        fdf_cross.groupby(["thematique", "tranche_vent"])["duree_h"].sum().reset_index(),
        x="thematique", y="duree_h", color="tranche_vent", barmode="stack",
        color_discrete_sequence=CHART_COLORS,
        labels={"duree_h": "Volume estimé (heures)", "thematique": "", "tranche_vent": "Tranche de vent"},
    )
    fig_cross_bar.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
    st.plotly_chart(fig_cross_bar, use_container_width=True)

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Détail / export — une ligne par séance x athlète, thématiques et tranches
# de vent résumées en texte (ex : "Portant (1.5h), Spi (0.5h)")
# ---------------------------------------------------------------------------
with st.expander("📋 Voir le détail des séances filtrées"):
    theme_summary = (
        fdf_theme.groupby(["session_id", "athlete"])
        .apply(lambda g: ", ".join(f"{r.thematique} ({r.duree_h:g}h)" for r in g.itertuples()))
        .rename("Thématiques")
    )
    wind_summary = (
        fdf_wind.groupby(["session_id", "athlete"])
        .apply(lambda g: ", ".join(f"{r.tranche_vent} ({r.duree_h:g}h)" for r in g.itertuples()))
        .rename("Tranches de vent")
    )

    detail = fdf_base.set_index(["session_id", "athlete"]).join(theme_summary).join(wind_summary).reset_index()
    display_df = detail[[
        "date", "groupe", "athlete", "lieu", "heure_debut", "heure_fin",
        "Thématiques", "Tranches de vent", "duree_h", "encadrant"
    ]].sort_values("date", ascending=False).rename(columns={
        "date": "Date", "groupe": "Groupe", "athlete": "Athlète", "lieu": "Lieu",
        "heure_debut": "Début", "heure_fin": "Fin", "duree_h": "Durée (h)", "encadrant": "Encadrant",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Exporter en CSV",
        display_df.to_csv(index=False).encode("utf-8"),
        file_name=f"suivi_voile_{start_date}_{end_date}.csv",
        mime="text/csv",
    )

st.markdown("<hr class='voile-divider'>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Comparaison tête-à-tête entre deux athlètes
# (indépendant des filtres ci-dessus, sauf la période, pour pouvoir toujours
#  comparer n'importe quel duo)
# ---------------------------------------------------------------------------
st.subheader("🆚 Comparer deux athlètes")

all_athlete_names = sorted(df_base["athlete"].unique())

if len(all_athlete_names) < 2:
    st.caption("Il faut au moins 2 athlètes actifs pour comparer.")
else:
    cA, cB = st.columns(2)
    athlete_a = cA.selectbox("Athlète A", all_athlete_names, index=0, key="cmp_athlete_a")
    idx_b = 1 if all_athlete_names[0] == athlete_a and len(all_athlete_names) > 1 else 0
    athlete_b = cB.selectbox("Athlète B", all_athlete_names, index=idx_b, key="cmp_athlete_b")

    if athlete_a == athlete_b:
        st.warning("Choisis deux athlètes différents.")
    else:
        period_mask = lambda d: (d["date"] >= pd.Timestamp(start_date)) & (d["date"] <= pd.Timestamp(end_date))
        duo = [athlete_a, athlete_b]
        duo_base = df_base[period_mask(df_base) & df_base["athlete"].isin(duo)]
        duo_theme = df_theme[period_mask(df_theme) & df_theme["athlete"].isin(duo)]
        duo_wind = df_wind[period_mask(df_wind) & df_wind["athlete"].isin(duo)]

        k1, k2 = st.columns(2)
        for col, name in zip([k1, k2], duo):
            sub = duo_base[duo_base["athlete"] == name]
            col.metric(name, f"{sub['duree_h'].sum():.1f} h", f"{sub['session_id'].nunique()} séances")

        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Volume par thématique**")
            if duo_theme.empty:
                st.caption("Pas de données sur cette période.")
            else:
                theme_duo_agg = duo_theme.groupby(["athlete", "thematique"])["duree_h"].sum().reset_index()
                fig_duo_theme = px.bar(
                    theme_duo_agg, x="thematique", y="duree_h", color="athlete", barmode="group",
                    color_discrete_sequence=[PALETTE["coral"], PALETTE["black"]],
                    labels={"duree_h": "Volume (heures)", "thematique": "", "athlete": ""},
                )
                fig_duo_theme.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
                st.plotly_chart(fig_duo_theme, use_container_width=True)

        with cc2:
            st.markdown("**Volume par tranche de vent**")
            if duo_wind.empty:
                st.caption("Pas de données sur cette période.")
            else:
                wind_duo_agg = duo_wind.groupby(["athlete", "tranche_vent"])["duree_h"].sum().reset_index()
                fig_duo_wind = px.bar(
                    wind_duo_agg, x="tranche_vent", y="duree_h", color="athlete", barmode="group",
                    color_discrete_sequence=[PALETTE["coral"], PALETTE["black"]],
                    labels={"duree_h": "Volume (heures)", "tranche_vent": "", "athlete": ""},
                )
                fig_duo_wind.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
                st.plotly_chart(fig_duo_wind, use_container_width=True)

        st.markdown("**Évolution du volume dans le temps**")
        duo_time = (
            duo_base.groupby([pd.Grouper(key="date", freq="W"), "athlete"])["duree_h"]
            .sum()
            .reset_index()
        )
        fig_duo_line = px.line(
            duo_time, x="date", y="duree_h", color="athlete", markers=True,
            color_discrete_sequence=[PALETTE["coral"], PALETTE["black"]],
            labels={"duree_h": "Volume (heures)", "date": "", "athlete": ""},
        )
        fig_duo_line.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
        st.plotly_chart(fig_duo_line, use_container_width=True)

db.close()
