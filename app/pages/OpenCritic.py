import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import t, load_games  # noqa: E402

st.title("Metacritic vs OpenCritic")

OC_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "opencritic.csv"
if not OC_PATH.exists():
    st.info(t(
        """
No OpenCritic data yet. To collect a comparison sample:

1. Create a free key on [RapidAPI — OpenCritic API](https://rapidapi.com/opencritic-opencritic-default/api/opencritic-api)
2. `export RAPIDAPI_KEY=...`
3. `python -m critiquemeta.opencritic --top 300`

The free quota is limited — the script resumes automatically across runs.
""",
        """
Pas encore de données OpenCritic. Pour collecter un échantillon comparatif :

1. Créer une clé gratuite sur [RapidAPI — OpenCritic API](https://rapidapi.com/opencritic-opencritic-default/api/opencritic-api)
2. `export RAPIDAPI_KEY=...`
3. `python -m critiquemeta.opencritic --top 300`

Le quota gratuit est limité — le script reprend automatiquement d'une exécution à l'autre.
"""))
    st.stop()

oc = pd.read_csv(OC_PATH)
games = load_games()
df = oc.merge(games.drop_duplicates("slug")[["slug", "platform", "genres"]],
              left_on="mc_slug", right_on="slug", how="left")
df = df[df["oc_score"].notna() & (df["oc_score"] > 0)]
df["mc_title"] = df["mc_title"].fillna(df["match"])

mc_scores = (games[games["meta_score"].notna()]
             .sort_values("meta_count", ascending=False)
             .drop_duplicates("slug")[["slug", "meta_score", "user_score"]])
df = df.merge(mc_scores, left_on="mc_slug", right_on="slug", how="left",
              suffixes=("", "_mc"))
df["oc_offset"] = df["meta_score"] - df["oc_score"]

st.markdown(t(
    f"""
{len(df):,} games matched between the two aggregators. OpenCritic's **Top Critic
Score** averages a curated pool of critics, while the **Metascore** is a weighted
average of a broader pool — comparing the two shows whether Metacritic's secret
weighting shifts scores in any direction.
""",
    f"""
{len(df):,} jeux appariés entre les deux agrégateurs. Le **Top Critic Score**
d'OpenCritic fait la moyenne d'un panel sélectionné de critiques, tandis que le
**Metascore** est une moyenne pondérée d'un panel plus large — la comparaison montre
si la pondération secrète de Metacritic décale les notes dans un sens ou l'autre.
"""))

c1, c2, c3 = st.columns(3)
c1.metric(t("Avg Metascore (sample)", "Metascore moyen (échantillon)"),
          f"{df['meta_score'].mean():.1f}")
c2.metric(t("Avg OpenCritic score", "Score OpenCritic moyen"),
          f"{df['oc_score'].mean():.1f}")
c3.metric(t("Avg difference (MC − OC)", "Écart moyen (MC − OC)"),
          f"{df['oc_offset'].mean():+.2f}")

fig = px.scatter(df, x="oc_score", y="meta_score", hover_data=["mc_title"],
                 color="oc_tier",
                 labels={"oc_score": t("OpenCritic Top Critic Score",
                                       "Top Critic Score OpenCritic"),
                         "meta_score": "Metascore",
                         "oc_tier": t("OC tier", "Palier OC")},
                 title=t("Metascore vs OpenCritic score, per game",
                         "Metascore vs score OpenCritic, par jeu"))
fig.add_shape(type="line", x0=40, y0=40, x1=100, y1=100, line=dict(color="white", width=1))
fig.update_layout(height=600)
st.plotly_chart(fig, use_container_width=True)

fig = px.histogram(df, x="oc_offset",
                   labels={"oc_offset": t("Metascore − OpenCritic score",
                                          "Metascore − score OpenCritic")},
                   title=t("Distribution of the difference between aggregators",
                           "Distribution de l'écart entre agrégateurs"))
fig.add_vline(x=0, line_color="red", line_width=1)
st.plotly_chart(fig, use_container_width=True)

st.markdown(t("### Biggest disagreements", "### Plus gros désaccords"))
cols = ["mc_title", "meta_score", "oc_score", "oc_offset", "oc_tier",
        "oc_num_reviews", "oc_percent_recommended"]
c1, c2 = st.columns(2)
with c1:
    st.markdown(t("**Metacritic more generous**", "**Metacritic plus généreux**"))
    st.dataframe(df.sort_values("oc_offset", ascending=False).head(10)[cols],
                 use_container_width=True, hide_index=True)
with c2:
    st.markdown(t("**OpenCritic more generous**", "**OpenCritic plus généreux**"))
    st.dataframe(df.sort_values("oc_offset").head(10)[cols],
                 use_container_width=True, hide_index=True)
