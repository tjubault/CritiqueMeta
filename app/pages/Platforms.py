import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, sidebar_filters, scored, long_scores,  # noqa: E402
                    dataset_caption, CATEGORY_ORDERS, PLATFORM_ORDER)

st.title(t("Platform view", "Vue par plateforme"))

df = sidebar_filters(load_games())
d = scored(df)
dataset_caption(df)

active_platforms = [p for p in PLATFORM_ORDER if p in df["platform"].unique()]
active_orders = {"platform": active_platforms, "score type": ["meta", "user"]}

tab_vol, tab_scores = st.tabs([t("Release volumes", "Volumes de sorties"),
                               t("Score distributions", "Distributions des notes")])

with tab_vol:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.histogram(df, x="platform", color="platform",
                           category_orders=active_orders,
                           title=t("Titles with a Metacritic page",
                                   "Titres ayant une fiche Metacritic"))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.histogram(d, x="platform", color="platform",
                           category_orders=active_orders,
                           title=t("Titles with both a Metascore and a user rating",
                                   "Titres avec Metascore et note joueurs"))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    tmp = df.groupby(["year", "platform"]).size().reset_index(name="titles")
    fig = px.line(tmp, x="year", y="titles", color="platform",
                  category_orders=active_orders,
                  labels={"titles": t("titles", "titres"), "year": t("year", "année")},
                  title=t("Titles released per year (platform life cycles)",
                          "Titres sortis par an (cycles de vie des plateformes)"))
    st.plotly_chart(fig, use_container_width=True)

with tab_scores:
    st.markdown(t(
        "Meta and user score distributions side by side, per platform. For most "
        "platforms the user-score median sits clearly below the Metascore median: "
        "**users are more severe than professional critics** — with Nintendo "
        "platforms somewhat spared.",
        "Distributions des notes méta et joueurs côte à côte, par plateforme. Sur la "
        "plupart des plateformes, la médiane des notes joueurs est nettement sous la "
        "médiane des Metascores : **les joueurs sont plus sévères que la critique "
        "professionnelle** — les plateformes Nintendo étant relativement épargnées."))
    df3 = long_scores(df)
    fig = px.box(df3, x="score", y="platform", color="score type", hover_name="title",
                 category_orders=active_orders,
                 title=t("Meta vs user score distributions per platform",
                         "Notes méta vs joueurs par plateforme"))
    fig.update_layout(height=max(500, 60 * len(active_platforms)))
    st.plotly_chart(fig, use_container_width=True)

    fig = px.box(d, x="offset", y="platform", color="platform", hover_name="title",
                 category_orders=active_orders,
                 title=t("Offset distribution per platform",
                         "Distribution de l'offset par plateforme"))
    fig.update_layout(showlegend=False,
                      height=max(500, 40 * d["platform"].nunique()))
    st.plotly_chart(fig, use_container_width=True)

    avg_off = (d.groupby("platform")["offset"].mean().reset_index()
               .sort_values("offset", ascending=True))
    fig = px.bar(avg_off, x="offset", y="platform", orientation="h", color="offset",
                 color_continuous_scale="RdBu_r", color_continuous_midpoint=0,
                 title=t("Average offset per platform",
                         "Offset moyen par plateforme"))
    fig.update_layout(height=max(400, 35 * len(avg_off)), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
