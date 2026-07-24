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
# Deux familles de tables :
#
#  - df_sess / df_sess_theme / df_sess_wind / df_sess_cross : 1 ligne PAR
#    SÉANCE (jamais multipliée par le nombre d'athlètes présents). C'est la
#    source utilisée pour tout ce qui n'est pas ventilé par athlète : volume
#    par groupe, volume par tranche de vent, par thématique, tranche x
#    thématique, KPIs globaux. Une séance de 2h à 5 athlètes compte pour 2h,
#    pas 10h.
#
#  - df_base / df_theme / df_wind / df_cross : 1 ligne = 1 athlète présent à
#    1 séance (ou 1 split). Utilisée uniquement quand le volume doit être
#    attribué à un athlète précis : comparaison "par athlète", comparaison
#    tête-à-tête, détail/export.
# ---------------------------------------------------------------------------
sess_rows, sess_theme_rows, sess_wind_rows, sess_cross_rows = [], [], [], []
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

    # --- niveau séance (une fois, indépendamment du nombre d'athlètes) ---
    sess_rows.append({**common, "duree_h": s.duration_hours})
    for ts in s.theme_splits:
        sess_theme_rows.append({**common, "thematique": ts.theme.name, "duree_h": ts.hours})
    for ws in s.wind_splits:
        sess_wind_rows.append({**common, "tranche_vent": ws.wind_tranche.label, "duree_h": ws.hours})
    if s.duration_hours > 0:
        for ts in s.theme_splits:
            for ws in s.wind_splits:
                est_hours = ts.hours * ws.hours / s.duration_hours
                sess_cross_rows.append({
                    **common, "thematique": ts.theme.name,
                    "tranche_vent": ws.wind_tranche.label, "duree_h": est_hours,
                })

    # --- niveau athlète (une ligne par athlète présent) ---
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

df_sess = pd.DataFrame(sess_rows)
df_sess_theme = pd.DataFrame(sess_theme_rows)
df_sess_wind = pd.DataFrame(sess_wind_rows)
df_sess_cross = pd.DataFrame(sess_cross_rows)

df_base = pd.DataFrame(base_rows)
df_theme = pd.DataFrame(theme_rows)
df_wind = pd.DataFrame(wind_rows)
df_cross = pd.DataFrame(cross_rows)

if df_sess.empty:
    st.warning(
        "Les séances enregistrées n'ont pas de répartition (thématique et/ou vent) renseignée. "
        "Vérifie la saisie."
    )
    st.stop()

for d in (df_sess, df_sess_theme, df_sess_wind, df_sess_cross, df_base, df_theme, df_wind, df_cross):
    d["date"] = pd.to_datetime(d["date"])

# ---------------------------------------------------------------------------
# Filtres (barre latérale)
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🔎 Filtres")

min_date, max_date = df_sess["date"].min().date(), df_sess["date"].max().date()
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
    group_names = sorted(df_sess["groupe"].unique())
    selected_entities = st.sidebar.multiselect("Groupes à comparer", group_names, default=group_names)
else:
    athlete_names = sorted(df_base["athlete"].unique())
    selected_entities = st.sidebar.multiselect(
        "Athlètes à comparer", athlete_names,
        default=athlete_names[: min(6, len(athlete_names))]
    )

theme_filter = st.sidebar.multiselect("Thématiques", sorted(df_sess_theme["thematique"].unique()))
tranche_filter = st.sidebar.multiselect("Tranches de vent", sorted(df_sess_wind["tranche_vent"].unique()))
spot_filter = st.sidebar.multiselect("Lieux", sorted(df_sess["lieu"].unique()))


def _period_spot_mask(d):
    m = (d["date"] >= pd.Timestamp(start_date)) & (d["date"] <= pd.Timestamp(end_date))
    if spot_filter:
        m &= d["lieu"].isin(spot_filter)
    return m


# -- séances autorisées par la période / le lieu --
sess_ps = df_sess[_period_spot_mask(df_sess)]
sess_theme_ps = df_sess_theme[_period_spot_mask(df_sess_theme)]
sess_wind_ps = df_sess_wind[_period_spot_mask(df_sess_wind)]

# -- restriction par entité (groupe ou athlète) --
if compare_mode == "Groupes":
    allowed_ids = set(sess_ps.loc[sess_ps["groupe"].isin(selected_entities), "session_id"]) if selected_entities else set(sess_ps["session_id"])
else:
    base_ps = df_base[_period_spot_mask(df_base)]
    if selected_entities:
        allowed_ids = set(base_ps.loc[base_ps["athlete"].isin(selected_entities), "session_id"])
    else:
        allowed_ids = set(sess_ps["session_id"])

if theme_filter:
    allowed_ids &= set(sess_theme_ps.loc[sess_theme_ps["thematique"].isin(theme_filter), "session_id"])
if tranche_filter:
    allowed_ids &= set(sess_wind_ps.loc[sess_wind_ps["tranche_vent"].isin(tranche_filter), "session_id"])

fdf_sess = sess_ps[sess_ps["session_id"].isin(allowed_ids)].copy()
fdf_sess_theme = sess_theme_ps[sess_theme_ps["session_id"].isin(allowed_ids)].copy()
fdf_sess_wind = sess_wind_ps[sess_wind_ps["session_id"].isin(allowed_ids)].copy()
fdf_sess_cross = df_sess_cross[_period_spot_mask(df_sess_cross) & df_sess_cross["session_id"].isin(allowed_ids)].copy()

fdf_base_all = df_base[_period_spot_mask(df_base) & df_base["session_id"].isin(allowed_ids)]
fdf_theme_all = df_theme[_period_spot_mask(df_theme) & df_theme["session_id"].isin(allowed_ids)]
fdf_wind_all = df_wind[_period_spot_mask(df_wind) & df_wind["session_id"].isin(allowed_ids)]

if compare_mode == "Athlètes" and selected_entities:
    fdf_base = fdf_base_all[fdf_base_all["athlete"].isin(selected_entities)].copy()
    fdf_theme = fdf_theme_all[fdf_theme_all["athlete"].isin(selected_entities)].copy()
    fdf_wind = fdf_wind_all[fdf_wind_all["athlete"].isin(selected_entities)].copy()
else:
    fdf_base = fdf_base_all.copy()
    fdf_theme = fdf_theme_all.copy()
    fdf_wind = fdf_wind_all.copy()

if fdf_sess.empty:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs — toujours au niveau séance (jamais multipliés par le nb d'athlètes)
# ---------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Volume total", f"{fdf_sess['duree_h'].sum():.1f} h",
    help="Somme des durées de séances filtrées, chaque séance comptée une seule fois "
         "(indépendamment du nombre d'athlètes présents)."
)
k2.metric("Séances (uniques)", f"{fdf_sess['session_id'].nunique()}")
k3.metric("Athlètes actifs", f"{fdf_base['athlete_id'].nunique()}")
dominant_tranche = fdf_sess_wind.groupby("tranche_vent")["duree_h"].sum().idxmax() if not fdf_sess_wind.empty else "—"
k4.metric("Tranche de vent dominante", dominant_tranche)

st.html("<hr class='voile-divider'>")

# ---------------------------------------------------------------------------
# Comparaison volume par entité
# ---------------------------------------------------------------------------
st.subheader(f"Volume total par {'groupe' if compare_mode == 'Groupes' else 'athlète'}")

if compare_mode == "Groupes":
    agg = fdf_sess.groupby("groupe")["duree_h"].sum().sort_values(ascending=True).reset_index()
else:
    agg = fdf_base.groupby("athlete")["duree_h"].sum().sort_values(ascending=True).reset_index()
    agg = agg.rename(columns={"athlete": entity_col})

fig_bar = px.bar(
    agg, x="duree_h", y=entity_col, orientation="h",
    text="duree_h", color_discrete_sequence=[PALETTE["coral"]],
    labels={"duree_h": "Volume (heures)", entity_col: ""},
)
fig_bar.update_traces(texttemplate="%{text:.1f} h", textposition="outside")
fig_bar.update_layout(plot_bgcolor="white", paper_bgcolor="white", showlegend=False, height=max(300, 40 * len(agg)))
st.plotly_chart(fig_bar, use_container_width=True, key="chart_bar_entite")

# ---------------------------------------------------------------------------
# Évolution temporelle
# ---------------------------------------------------------------------------
st.subheader("Évolution du volume dans le temps")
granularity = st.radio("Granularité", ["Semaine", "Mois"], horizontal=True, label_visibility="collapsed")
freq = "W" if granularity == "Semaine" else "M"

if compare_mode == "Groupes":
    time_agg = (
        fdf_sess.groupby([pd.Grouper(key="date", freq=freq), "groupe"])["duree_h"]
        .sum()
        .reset_index()
    )
else:
    time_agg = (
        fdf_base.groupby([pd.Grouper(key="date", freq=freq), "athlete"])["duree_h"]
        .sum()
        .reset_index()
        .rename(columns={"athlete": entity_col})
    )

fig_line = px.line(
    time_agg, x="date", y="duree_h", color=entity_col, markers=True,
    color_discrete_sequence=CHART_COLORS,
    labels={"duree_h": "Volume (heures)", "date": "", entity_col: ""},
)
fig_line.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
st.plotly_chart(fig_line, use_container_width=True, key="chart_line_temps")

st.html("<hr class='voile-divider'>")

# ---------------------------------------------------------------------------
# Analyse par tranche de vent / thématique — toujours au niveau séance
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Volume par tranche de vent")
    if fdf_sess_wind.empty:
        st.caption("Pas de données pour les filtres actuels.")
    else:
        wind_agg = fdf_sess_wind.groupby("tranche_vent")["duree_h"].sum().reset_index()
        fig_wind = px.pie(
            wind_agg, names="tranche_vent", values="duree_h", hole=0.55,
            color_discrete_sequence=CHART_COLORS,
        )
        fig_wind.update_traces(textinfo="percent+label")
        fig_wind.update_layout(showlegend=False)
        st.plotly_chart(fig_wind, use_container_width=True, key="chart_wind_pie")

with c2:
    st.subheader("Volume par thématique")
    if fdf_sess_theme.empty:
        st.caption("Pas de données pour les filtres actuels.")
    else:
        theme_agg = fdf_sess_theme.groupby("thematique")["duree_h"].sum().reset_index().sort_values("duree_h")
        fig_theme = px.bar(
            theme_agg, x="duree_h", y="thematique", orientation="h",
            color_discrete_sequence=[PALETTE["black"]],
            labels={"duree_h": "Volume (heures)", "thematique": ""},
        )
        fig_theme.update_layout(plot_bgcolor="white", paper_bgcolor="white", height=max(300, 35 * len(theme_agg)))
        st.plotly_chart(fig_theme, use_container_width=True, key="chart_theme_bar")

# ---------------------------------------------------------------------------
# Croisement entité x tranche de vent (heatmap) — utile pour comparer profils
# ---------------------------------------------------------------------------
st.subheader(f"Répartition croisée : {'groupe' if compare_mode == 'Groupes' else 'athlète'} × tranche de vent")

if compare_mode == "Groupes":
    cross_src = fdf_sess_wind
    idx_col = "groupe"
else:
    cross_src = fdf_wind
    idx_col = "athlete"

if cross_src.empty:
    st.caption("Pas de données pour les filtres actuels.")
else:
    cross = cross_src.pivot_table(index=idx_col, columns="tranche_vent", values="duree_h", aggfunc="sum", fill_value=0)
    fig_heat = go.Figure(data=go.Heatmap(
        z=cross.values, x=cross.columns, y=cross.index,
        colorscale=[[0, "#FFFFFF"], [1, PALETTE["coral"]]],
        text=cross.values.round(1), texttemplate="%{text}",
        colorbar=dict(title="heures"),
    ))
    fig_heat.update_layout(height=max(300, 40 * len(cross)), paper_bgcolor="white")
    st.plotly_chart(fig_heat, use_container_width=True, key="chart_heat_entite_vent")

st.html("<hr class='voile-divider'>")

# ---------------------------------------------------------------------------
# Thématiques travaillées en fonction de la force du vent — niveau séance
# ---------------------------------------------------------------------------
st.subheader("Thématiques travaillées par tranche de vent")
st.caption(
    "Estimation : le temps de chaque thématique est réparti au prorata des tranches de vent "
    "de la séance (on suppose un mix de conditions homogène sur toute la séance). Chaque séance "
    "est comptée une seule fois."
)
if fdf_sess_cross.empty:
    st.caption("Pas de données pour les filtres actuels.")
else:
    cross_theme_wind = fdf_sess_cross.pivot_table(
        index="thematique", columns="tranche_vent", values="duree_h", aggfunc="sum", fill_value=0
    )
    fig_cross = go.Figure(data=go.Heatmap(
        z=cross_theme_wind.values, x=cross_theme_wind.columns, y=cross_theme_wind.index,
        colorscale=[[0, "#FFFFFF"], [1, PALETTE["black"]]],
        text=cross_theme_wind.values.round(1), texttemplate="%{text}",
        colorbar=dict(title="heures (est.)"),
    ))
    fig_cross.update_layout(height=max(300, 40 * len(cross_theme_wind)), paper_bgcolor="white")
    st.plotly_chart(fig_cross, use_container_width=True, key="chart_cross_heat")

    fig_cross_bar = px.bar(
        fdf_sess_cross.groupby(["thematique", "tranche_vent"])["duree_h"].sum().reset_index(),
        x="thematique", y="duree_h", color="tranche_vent", barmode="stack",
        color_discrete_sequence=CHART_COLORS,
        labels={"duree_h": "Volume estimé (heures)", "thematique": "", "tranche_vent": "Tranche de vent"},
    )
    fig_cross_bar.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
    st.plotly_chart(fig_cross_bar, use_container_width=True, key="chart_cross_bar")

st.html("<hr class='voile-divider'>")

# ---------------------------------------------------------------------------
# Détail / export — une ligne par séance x athlète (vue de présence),
# thématiques et tranches de vent résumées en texte
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
    st.caption("Une ligne par athlète présent — la durée indiquée est celle de la séance (pas cumulée).")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Exporter en CSV",
        display_df.to_csv(index=False).encode("utf-8"),
        file_name=f"suivi_voile_{start_date}_{end_date}.csv",
        mime="text/csv",
    )

st.html("<hr class='voile-divider'>")

# ---------------------------------------------------------------------------
# Comparaison tête-à-tête entre deux athlètes
# (indépendant des filtres ci-dessus, sauf la période, pour pouvoir toujours
#  comparer n'importe quel duo — déjà correct : volumes propres à chaque athlète)
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
                st.plotly_chart(fig_duo_theme, use_container_width=True, key="chart_duo_theme")

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
                st.plotly_chart(fig_duo_wind, use_container_width=True, key="chart_duo_wind")

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
        st.plotly_chart(fig_duo_line, use_container_width=True, key="chart_duo_line")

db.close()
