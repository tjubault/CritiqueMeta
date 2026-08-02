import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, load_reviews, sidebar_filters, scored,  # noqa: E402
                    dataset_caption, CATEGORY_ORDERS, term)

st.title(t("Game viewpoint", "Point de vue jeu"))

df = sidebar_filters(load_games())
d = scored(df)
dataset_caption(df)

tab_scatter, tab_explorer = st.tabs([t("Meta vs user scatter", "Nuage méta vs joueurs"),
                                     t("Game explorer", "Explorateur de jeux")])

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
                     title=t("Meta and user scores per game",
                             "Notes méta et joueurs par jeu"))
    fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100, line=dict(color="white", width=1))
    fig.update_layout(height=650)
    st.plotly_chart(fig, use_container_width=True)

with tab_explorer:
    search = st.text_input(t("Search a title", "Chercher un titre"))
    cols = ["title", "platform", "year", "developer", "genres",
            "meta_score", "n_user_score", "offset", "meta_count", "user_count", "ratio"]
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

    st.markdown(t("#### Individual reviews for one game",
                  "#### Avis individuels d'un jeu"))
    options = table["title"].unique()[:2000]
    pick = st.selectbox(t("Pick a game", "Choisir un jeu"), options, index=None,
                        placeholder=t("Choose a title to inspect its reviews…",
                                      "Choisissez un titre pour voir ses avis…"))
    if pick:
        meta_r = load_reviews("meta_reviews")
        user_r = load_reviews("user_reviews")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(t("**Critic reviews**", "**Avis critiques**"))
            if meta_r.empty:
                st.info(t("No critic reviews collected yet (`scrape.py reviews-critic`).",
                          "Avis critiques pas encore collectés (`scrape.py reviews-critic`)."))
            else:
                sel = meta_r[meta_r["title"] == pick][["score", "critic", "date", "platform"]]
                st.dataframe(sel.sort_values("score", ascending=False),
                             use_container_width=True, hide_index=True)
        with c2:
            st.markdown(t("**User reviews**", "**Avis joueurs**"))
            if user_r.empty:
                st.info(t("No user reviews collected yet (`scrape.py reviews-user`).",
                          "Avis joueurs pas encore collectés (`scrape.py reviews-user`)."))
            else:
                sel = user_r[user_r["title"] == pick][["score", "user", "date", "platform"]]
                st.dataframe(sel.sort_values("date", ascending=False),
                             use_container_width=True, hide_index=True)
