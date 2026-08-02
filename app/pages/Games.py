import sys
from pathlib import Path

import numpy as np
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, load_reviews, sidebar_filters, scored,  # noqa: E402
                    dataset_caption, CATEGORY_ORDERS, term)

st.title(t("Game viewpoint", "Point de vue jeu"))

df = sidebar_filters(load_games())
d = scored(df)
dataset_caption(df)

tab_scatter, tab_cross, tab_explorer = st.tabs([
    t("Scores per game & platform", "Notes par jeu et plateforme"),
    t("Cross-platform view", "Vue multi-plateforme"),
    t("Game explorer", "Explorateur de jeux"),
])

# --- Tab 1: per-platform scatter (existing, with platform in title) --------
with tab_scatter:
    st.markdown(t(
        f"""
Each point is a game on a platform: **X = Metascore, Y = user score**. On the white
diagonal both agree; *below* it users were harsher than critics, *above* it they were
more generous. Circle size is the {term("ratio", "ratio")} (user ratings per critic
review) — big circles flag review-bombing candidates. Click legend items to toggle
platforms.
""",
        f"""
Chaque point est un jeu sur une plateforme : **X = Metascore, Y = note joueurs**. Sur
la diagonale blanche, tout le monde est d'accord ; *en dessous*, les joueurs ont été
plus durs que la critique, *au-dessus*, plus généreux. La taille du cercle est le
{term("ratio", "ratio")} (notes joueurs par avis critique) — les gros cercles
signalent les candidats au review bombing. Cliquez sur la légende pour filtrer les
plateformes.
"""), unsafe_allow_html=True)
    has_ratio = d["ratio"].notna()
    min_ratio = st.slider(t("Only games with ratio ≥", "Seulement les jeux au ratio ≥"),
                          0, 100, 0,
                          help=t("0 shows every game (games without ratio data included)",
                                 "0 montre tous les jeux (y compris sans donnée de ratio)"))
    plot_df = d if min_ratio == 0 else d[has_ratio & (d["ratio"] >= min_ratio)]
    size = "ratio" if (min_ratio > 0 or has_ratio.all()) and plot_df["ratio"].notna().all() else None

    fig = px.scatter(plot_df, x="meta_score", y="n_user_score", color="platform",
                     hover_data=["title", "year"], size=size, trendline="ols",
                     category_orders=CATEGORY_ORDERS,
                     labels={"n_user_score": t("User score", "Note joueurs"),
                             "meta_score": t("Meta score", "Note méta")},
                     title=t("Meta and user scores per game & platform",
                             "Notes méta et joueurs par jeu et plateforme"))
    fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100, line=dict(color="white", width=1))
    fig.update_layout(height=650)
    st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: cross-platform aggregation -------------------------------------
with tab_cross:
    st.markdown(t(
        """
Games that exist on multiple platforms, aggregated: scores are **weighted averages**
(weighted by the number of critic or user reviews). This removes the per-platform
noise and shows the "consensus" score for each title.
""",
        """
Jeux existant sur plusieurs plateformes, agrégés : les scores sont des **moyennes
pondérées** (pondérées par le nombre de critiques ou de joueurs). Cela retire le bruit
par plateforme et montre le score « de consensus » pour chaque titre.
"""))

    agg = (d.groupby("title")
           .apply(lambda g: {
               "meta_score": np.average(g["meta_score"], weights=g["meta_count"]),
               "n_user_score": np.average(g["n_user_score"],
                                          weights=g["user_count"].fillna(1)),
               "meta_count": g["meta_count"].sum(),
               "user_count": g["user_count"].sum(),
               "platforms": g["platform"].nunique(),
               "year": g["year"].min(),
           }, include_groups=False)
           .apply(lambda s: dict(s))  # noqa – already a dict
           )
    cross = agg.apply(lambda x: x).apply(lambda x: x if isinstance(x, dict) else {})
    import pandas as pd
    cross = pd.DataFrame(cross.tolist(), index=agg.index).reset_index()
    cross["offset"] = cross["meta_score"] - cross["n_user_score"]
    cross["ratio"] = cross["user_count"] / cross["meta_count"]

    fig = px.scatter(cross, x="meta_score", y="n_user_score",
                     hover_data=["title", "platforms", "year"],
                     size="meta_count",
                     labels={"n_user_score": t("User score (weighted avg)",
                                               "Note joueurs (moy. pondérée)"),
                             "meta_score": t("Metascore (weighted avg)",
                                             "Metascore (moy. pondérée)")},
                     title=t("Cross-platform scores per game",
                             "Scores multi-plateformes par jeu"))
    fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100,
                  line=dict(color="white", width=1))
    fig.update_layout(height=650)
    st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: game explorer with search + cross-platform summary -------------
with tab_explorer:
    search = st.text_input(t("Search a title", "Chercher un titre"))

    cols = ["title", "platform", "year", "meta_score", "n_user_score",
            "offset", "meta_count", "user_count", "ratio"]
    table = d[cols].sort_values("meta_score", ascending=False)
    if search:
        table = table[table["title"].str.contains(search, case=False, na=False)]
    st.dataframe(
        table, use_container_width=True, height=420, hide_index=True,
        column_config={
            "n_user_score": st.column_config.NumberColumn(
                t("user score", "note joueurs"), format="%.0f"),
            "meta_score": st.column_config.NumberColumn("metascore"),
            "offset": st.column_config.NumberColumn(format="%.0f"),
            "ratio": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    st.markdown(t("#### Game detail", "#### Détail d'un jeu"))
    options = table["title"].unique()[:2000]
    pick = st.selectbox(t("Pick a game", "Choisir un jeu"), options, index=None,
                        placeholder=t("Choose a title…", "Choisissez un titre…"))
    if pick:
        sel = d[d["title"] == pick][cols]
        st.markdown(t(f"**{pick}** — per platform:", f"**{pick}** — par plateforme :"))
        st.dataframe(sel, use_container_width=True, hide_index=True,
                     column_config={
                         "n_user_score": st.column_config.NumberColumn(
                             t("user score", "note joueurs"), format="%.0f"),
                         "meta_score": st.column_config.NumberColumn("metascore"),
                         "offset": st.column_config.NumberColumn(format="%.0f"),
                         "ratio": st.column_config.NumberColumn(format="%.1f"),
                     })

        total_meta_count = sel["meta_count"].sum()
        total_user_count = sel["user_count"].sum()
        avg_meta = np.average(sel["meta_score"], weights=sel["meta_count"])
        weights_user = sel["user_count"].fillna(1)
        avg_user = np.average(sel["n_user_score"], weights=weights_user)
        combined_ratio = total_user_count / total_meta_count if total_meta_count else 0

        st.markdown(t("**All platforms combined:**", "**Toutes plateformes confondues :**"))
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(t("Metascore (weighted)", "Metascore (pondéré)"), f"{avg_meta:.1f}")
        m2.metric(t("User score (weighted)", "Note joueurs (pondérée)"), f"{avg_user:.1f}")
        m3.metric(t("Critic reviews", "Avis critiques"), f"{total_meta_count:,}")
        m4.metric(t("User ratings", "Notes joueurs"), f"{total_user_count:,.0f}")
        m5.metric(t("Combined ratio", "Ratio combiné"), f"{combined_ratio:.1f}")
