import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, sidebar_filters, scored,  # noqa: E402
                    dataset_caption, CATEGORY_ORDERS)

st.title(t("Developers", "Développeurs"))

df = sidebar_filters(load_games())
d = scored(df)
dataset_caption(df)

if d["developer"].isna().all():
    st.warning(t("Developer info is not collected yet — run "
                 "`python -m critiquemeta.scrape details`, then "
                 "`python -m critiquemeta.clean`.",
                 "Les développeurs ne sont pas encore collectés — lancer "
                 "`python -m critiquemeta.scrape details`, puis "
                 "`python -m critiquemeta.clean`."))
    st.stop()

dev = (d.dropna(subset=["developer"])
       .groupby("developer")
       .agg(avg_offset=("offset", "mean"), num_games=("title", "size"),
            avg_meta=("meta_score", "mean"), avg_user=("n_user_score", "mean"),
            avg_ratio=("ratio", "mean"))
       .reset_index())

min_games = st.sidebar.slider(t("Min. games per developer", "Min. de jeux par studio"),
                              1, 50, 5)
big = dev[dev["num_games"] >= min_games]

st.markdown(t(
    f"""
{len(dev):,} developers in the current selection; {len(big):,} released
**{min_games}+ rated games** and are shown in the scatter. Studios far below the
white diagonal are systematically better rated by critics than by their players.
""",
    f"""
{len(dev):,} studios dans la sélection courante ; {len(big):,} ont sorti
**{min_games}+ jeux notés** et figurent dans le nuage. Les studios loin sous la
diagonale blanche sont systématiquement mieux notés par la critique que par leurs
joueurs.
"""))

fig = px.scatter(big, x="avg_meta", y="avg_user", hover_data=["developer", "num_games"],
                 size="num_games",
                 labels={"avg_meta": t("Average Metascore", "Metascore moyen"),
                         "avg_user": t("Average user score", "Note joueurs moyenne"),
                         "num_games": t("games", "jeux")},
                 title=t("Average user score vs average Metascore per developer",
                         "Note joueurs moyenne vs Metascore moyen par studio"))
lo = min(big["avg_meta"].min(), big["avg_user"].min()) - 2 if not big.empty else 0
hi = max(big["avg_meta"].max(), big["avg_user"].max()) + 2 if not big.empty else 100
fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(color="white", width=1))
fig.update_layout(height=600)
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown(t("**Most critic-overrated studios** (highest avg offset)",
                  "**Studios les plus survalorisés par la critique** (offset moyen le plus haut)"))
    st.dataframe(big.sort_values("avg_offset", ascending=False).head(15),
                 use_container_width=True, hide_index=True)
with c2:
    st.markdown(t("**Most user-favoured studios** (lowest avg offset)",
                  "**Studios chouchous des joueurs** (offset moyen le plus bas)"))
    st.dataframe(big.sort_values("avg_offset").head(15),
                 use_container_width=True, hide_index=True)

st.markdown(t("### One developer in detail", "### Un studio en détail"))
pick = st.selectbox(t("Developer", "Studio"),
                    dev.sort_values("num_games", ascending=False)["developer"],
                    index=None, placeholder=t("Choose a studio…", "Choisissez un studio…"))
if pick:
    studio_games = d[d["developer"] == pick].sort_values("year", ascending=False)

    st.dataframe(
        studio_games[["title", "platform", "year", "meta_score", "n_user_score",
                       "offset", "meta_count", "user_count", "ratio"]],
        use_container_width=True, hide_index=True, height=400,
        column_config={
            "n_user_score": st.column_config.NumberColumn(
                t("user score", "note joueurs"), format="%.0f"),
            "meta_score": st.column_config.NumberColumn("metascore"),
            "offset": st.column_config.NumberColumn(format="%.0f"),
            "ratio": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    by_year = studio_games.groupby("year").agg(
        meta=("meta_score", "mean"), user=("n_user_score", "mean")).reset_index()
    fig = px.line(by_year, x="year", y=["meta", "user"],
                  labels={"year": t("year", "année"), "value": t("score", "note"),
                          "variable": t("score type", "type de note")},
                  title=t(f"Average scores over time — {pick}",
                          f"Notes moyennes au cours du temps — {pick}"))
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    vol_plat = studio_games.groupby(["year", "platform"]).size().reset_index(name="games")
    fig = px.bar(vol_plat, x="year", y="games", color="platform",
                 category_orders=CATEGORY_ORDERS,
                 labels={"year": t("year", "année"), "games": t("games", "jeux")},
                 title=t(f"Games released per year by platform — {pick}",
                         f"Jeux sortis par année et plateforme — {pick}"))
    st.plotly_chart(fig, use_container_width=True)
