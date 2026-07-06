import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import t, load_games, load_reviews, scored  # noqa: E402

st.title(t("Critic publications", "Rédactions critiques"))

meta_r = load_reviews("meta_reviews")
if meta_r.empty:
    st.warning(t("Individual critic reviews are not collected yet — run "
                 "`python -m critiquemeta.scrape reviews-critic`, then "
                 "`python -m critiquemeta.clean`.",
                 "Les avis critiques individuels ne sont pas encore collectés — lancer "
                 "`python -m critiquemeta.scrape reviews-critic`, puis "
                 "`python -m critiquemeta.clean`."))
    st.stop()

games = scored(load_games())

# offset de chaque avis par rapport au score utilisateur du jeu
rev = meta_r.merge(
    games[["slug", "platform_slug", "n_user_score"]],
    on=["slug", "platform_slug"], how="inner")
rev["offset"] = rev["score"] - rev["n_user_score"]

critics = (rev.groupby("critic")
           .agg(avg_score=("score", "mean"), avg_offset=("offset", "mean"),
                num_reviews=("score", "size"))
           .reset_index())

min_reviews = st.sidebar.slider(t("Min. reviews per publication",
                                  "Min. d'avis par rédaction"), 1, 500, 50)
big = critics[critics["num_reviews"] >= min_reviews]

st.markdown(t(
    f"""
{len(critics):,} publications have reviewed at least one game in the dataset;
{len(big):,} have **{min_reviews}+ reviews** and are shown below.

**Average offset** compares each publication's scores to the user score of the same
games: a publication with a high average offset consistently scores games above what
users think of them.
""",
    f"""
{len(critics):,} rédactions ont testé au moins un jeu du jeu de données ;
{len(big):,} comptent **{min_reviews}+ avis** et sont affichées ci-dessous.

L'**offset moyen** compare les notes de chaque rédaction à la note joueurs des mêmes
jeux : une rédaction à l'offset moyen élevé note systématiquement au-dessus de l'avis
des joueurs.
"""))

fig = px.scatter(big, x="avg_offset", y="avg_score", size="num_reviews",
                 hover_data=["critic"],
                 labels={"avg_offset": t("Average offset vs users",
                                         "Offset moyen vs joueurs"),
                         "avg_score": t("Average score given", "Note moyenne donnée"),
                         "num_reviews": t("Number of reviews", "Nombre d'avis")},
                 title=t("Average score vs average offset for each publication",
                         "Note moyenne vs offset moyen par rédaction"))
fig.add_vline(x=0, line_color="red", line_width=1)
fig.update_layout(height=600)
st.plotly_chart(fig, use_container_width=True)

fig = px.bar(big.sort_values("num_reviews", ascending=False),
             x="critic", y="num_reviews", color="avg_score",
             labels={"num_reviews": t("Games reviewed", "Jeux testés"),
                     "critic": t("publication", "rédaction"),
                     "avg_score": t("avg score", "note moyenne")},
             title=t("Games reviewed per publication", "Jeux testés par rédaction"))
fig.update_xaxes(visible=False)
st.plotly_chart(fig, use_container_width=True)

st.markdown(t("### Score distribution of one publication",
              "### Distribution des notes d'une rédaction"))
pick = st.selectbox(t("Publication", "Rédaction"),
                    critics.sort_values("num_reviews", ascending=False)["critic"],
                    index=None,
                    placeholder=t("Choose a publication…", "Choisissez une rédaction…"))
if pick:
    sel = meta_r[meta_r["critic"] == pick]
    fig = px.histogram(sel, x="score", marginal="box",
                       title=t(f"Score distribution for {pick} ({len(sel):,} reviews)",
                               f"Distribution des notes de {pick} ({len(sel):,} avis)"))
    st.plotly_chart(fig, use_container_width=True)
