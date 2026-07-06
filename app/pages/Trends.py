import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, sidebar_filters, scored, long_scores,  # noqa: E402
                    dataset_caption, CATEGORY_ORDERS)

st.title(t("Trends over time", "Tendances dans le temps"))

df = sidebar_filters(load_games())
d = scored(df)
dataset_caption(df)

df3 = long_scores(df)

tmp = df3.groupby(["year", "score type"])["score"].mean().reset_index()
fig = px.line(tmp, x="year", y="score", color="score type",
              category_orders=CATEGORY_ORDERS,
              labels={"year": t("year", "année")},
              title=t("Average meta and user scores per year",
                      "Notes méta et joueurs moyennes par année"))
st.plotly_chart(fig, use_container_width=True)

tmp = d.groupby("year")["offset"].agg(["mean", "std"]).reset_index()
fig = px.line(tmp, x="year", y="mean", error_y="std",
              labels={"mean": "offset", "year": t("year", "année")},
              title=t("Average offset per year (±1σ)", "Offset moyen par année (±1σ)"))
fig.add_hline(y=0, line_color="red", line_width=1)
st.plotly_chart(fig, use_container_width=True)

tmp = d.groupby(["year", "platform"])["offset"].mean().reset_index()
fig = px.line(tmp, x="year", y="offset", color="platform",
              category_orders=CATEGORY_ORDERS,
              labels={"year": t("year", "année")},
              title=t("Average offset per platform, per year",
                      "Offset moyen par plateforme et par année"))
st.plotly_chart(fig, use_container_width=True)

st.markdown(t("### Every game through time", "### Tous les jeux dans le temps"))
metric = st.radio("Metric", ["meta_score", "n_user_score", "offset"], horizontal=True,
                  label_visibility="collapsed",
                  format_func=lambda m: {
                      "meta_score": "Metascore",
                      "n_user_score": t("User score", "Note joueurs"),
                      "offset": "Offset"}[m])
fig = px.scatter(d, x="release_date", y=metric, color="platform", trendline="ols",
                 hover_data=["title"], category_orders=CATEGORY_ORDERS,
                 labels={"release_date": t("Release date", "Date de sortie")},
                 title=t(f"{metric} through time", f"{metric} dans le temps"))
fig.update_layout(height=600)
st.plotly_chart(fig, use_container_width=True)
