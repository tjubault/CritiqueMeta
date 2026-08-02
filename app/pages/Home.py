import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import t, load_games, scored, dataset_caption, term  # noqa: E402

st.title("🎮 CritiqueMeta")
st.markdown(t(
    """
*A walk around Metacritic scores for video games.*

- **Are users getting tougher?**
- **Are ratings constantly increasing?**
- **Is the gap between critic and user scores growing?**
- **What explains it?**

The dataset covers the entire Metacritic games catalog (all platforms, PC included),
collected through Metacritic's JSON API.
""",
    """
*Une promenade dans les notes Metacritic des jeux vidéo.*

- **Les joueurs deviennent-ils plus sévères ?**
- **Les notes augmentent-elles sans cesse ?**
- **Le gap entre les notes des critiques et des joueurs augmente-t-il ?**
- **Qu'est-ce qui l'explique ?**

Le jeu de données couvre l'intégralité du catalogue Metacritic (toutes plateformes,
PC inclus), collecté via l'API JSON de Metacritic.
"""))

df = load_games()
d = scored(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric(t("Title-platform entries", "Entrées titre-plateforme"), f"{len(df):,}")
c2.metric(t("With both scores", "Avec les deux notes"), f"{len(d):,}")
c3.metric(t("Platforms", "Plateformes"), df["platform"].nunique())
c4.metric(t("Avg offset (meta − user)", "Offset moyen (méta − joueurs)"),
          f"{d['offset'].mean():+.1f}")

st.markdown(t(
    f"""
### How to read this app

| Metric | Definition |
| --- | --- |
| **{term("metascore")}** | Weighted average of professional critic reviews (0–100) |
| **{term("user_score")}** | Average of user ratings (0–10, shown here ×10 to match the Metascore scale) |
| **{term("offset")}** | Metascore minus (-) user score. Positive → critics liked the game more than users |
| **{term("ratio")}** | (Number of user ratings) divided by (number of critic reviews).<br>High ratio → influx of players (potential review bombing, or a live-event game) |

Use the pages in the sidebar to explore distributions, platforms, individual games,
critic publications, developers and time trends. Every page shares the same sidebar filters.
""",
    f"""
### Comment lire cette app

| Métrique | Définition |
| --- | --- |
| **{term("metascore")}** | Moyenne pondérée des critiques professionnelles (0–100) |
| **{term("user_score")}** | Moyenne des notes des joueurs (0–10, affichée ici ×10 pour être comparable au Metascore) |
| **{term("offset")}** | Metascore moins (-) note joueurs. Positif → les critiques ont préféré le jeu aux joueurs |
| **{term("ratio")}** | (Nombre de notes joueurs) divisé par (nombre d'avis critique pro).<br>Ratio élevé → afflux de joueurs (review bombing potentiel, ou jeu évènement) |

Les pages du menu latéral explorent les distributions, les plateformes, les jeux un à
un, les rédactions, les développeurs et les tendances temporelles. Toutes partagent
les mêmes filtres latéraux.
"""), unsafe_allow_html=True)

dataset_caption(df)
st.caption(t(
    f"Most recent release in dataset: {df['release_date'].max():%B %d, %Y}",
    f"Sortie la plus récente du jeu de données : {df['release_date'].max():%d/%m/%Y}"))
