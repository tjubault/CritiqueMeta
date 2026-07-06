import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, sidebar_filters, scored, long_scores,  # noqa: E402
                    dataset_caption, CATEGORY_ORDERS)

st.title(t("Platform view", "Vue par plateforme"))

df = sidebar_filters(load_games())
d = scored(df)
dataset_caption(df)

tab_vol, tab_scores = st.tabs([t("Release volumes", "Volumes de sorties"),
                               t("Score distributions", "Distributions des notes")])

with tab_vol:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.histogram(df, x="platform", color="platform",
                           category_orders=CATEGORY_ORDERS,
                           title=t("Titles with a Metacritic page",
                                   "Titres ayant une fiche Metacritic"))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.histogram(d, x="platform", color="platform",
                           category_orders=CATEGORY_ORDERS,
                           title=t("Titles with both a Metascore and a user rating",
                                   "Titres avec Metascore et note joueurs"))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    tmp = df.groupby(["year", "platform"]).size().reset_index(name="titles")
    fig = px.line(tmp, x="year", y="titles", color="platform",
                  category_orders=CATEGORY_ORDERS,
                  labels={"titles": t("titles", "titres"), "year": t("year", "année")},
                  title=t("Titles released per year (platform life cycles)",
                          "Titres sortis par an (cycles de vie des plateformes)"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(t(
        "Release cycle over a calendar year — the November peak (holiday "
        "season) shows on every platform, with a smaller one in March.",
        "Cycle de sortie sur une année civile — le pic de novembre (fêtes de fin "
        "d'année) apparaît sur toutes les plateformes, avec un pic secondaire en mars."))
    tmp = df.groupby(["month", "platform"]).size().reset_index(name="titles")
    fig = px.line(tmp, x="month", y="titles", color="platform",
                  category_orders=CATEGORY_ORDERS,
                  labels={"titles": t("titles", "titres"), "month": t("month", "mois")},
                  title=t("Titles released per month of the year (all years combined)",
                          "Titres sortis par mois de l'année (toutes années confondues)"))
    fig.update_xaxes(dtick=1)
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
                 category_orders=CATEGORY_ORDERS,
                 title=t("Meta vs user score distributions per platform",
                         "Notes méta vs joueurs par plateforme"))
    fig.update_layout(height=max(500, 60 * df3["platform"].nunique()))
    st.plotly_chart(fig, use_container_width=True)

    fig = px.box(d, x="offset", y="platform", color="platform", hover_name="title",
                 category_orders=CATEGORY_ORDERS,
                 title=t("Offset distribution per platform",
                         "Distribution de l'offset par plateforme"))
    fig.update_layout(showlegend=False,
                      height=max(500, 40 * d["platform"].nunique()))
    st.plotly_chart(fig, use_container_width=True)
