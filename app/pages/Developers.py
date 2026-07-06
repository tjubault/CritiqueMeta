import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, sidebar_filters, scored, long_scores,  # noqa: E402
                    dataset_caption)

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
    df3 = long_scores(df)
    tmp = (df3[df3["developer"] == pick]
           .groupby(["title", "score type", "first_release"])["score"].mean()
           .reset_index().sort_values("first_release"))
    fig = px.histogram(tmp, x="title", y="score", color="score type", barmode="group",
                       category_orders={"score type": ["meta", "user"]},
                       title=t(f"Meta vs user scores — {pick}",
                               f"Notes méta vs joueurs — {pick}"))
    fig.update_yaxes(title="score")
    st.plotly_chart(fig, use_container_width=True)
