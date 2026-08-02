import sys
from pathlib import Path

import plotly.express as px
import plotly.figure_factory as ff
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (t, load_games, sidebar_filters, scored, long_scores,  # noqa: E402
                    dataset_caption, term, CATEGORY_ORDERS)

st.title(t("Score distributions", "Distributions des notes"))

df = sidebar_filters(load_games())
d = scored(df)
dataset_caption(df)

st.markdown(t(
    """
All platforms combined, how are Metascores and user scores distributed?
Two skewed distributions (the average is well above 50), shifted relative to each
other: **users are more severe on average**. Note the accumulation points — users
love round numbers like 50, while 80 is the mode of the Metascore distribution.
""",
    """
Toutes plateformes confondues, comment se répartissent les Metascores et les notes
joueurs ? Deux distributions asymétriques (la moyenne est bien au-dessus de 50),
décalées l'une par rapport à l'autre : **les joueurs sont en moyenne plus sévères**.
Notez les points d'accumulation — les joueurs adorent les chiffres ronds comme 50,
tandis que 80 est le mode de la distribution des Metascores.
"""))

c1, c2 = st.columns(2)
c1.metric(t("Average Metascore", "Metascore moyen"), f"{d['meta_score'].mean():.1f}")
c2.metric(t("Average user score", "Note joueurs moyenne"), f"{d['n_user_score'].mean():.1f}")

df3 = long_scores(df)
fig = px.histogram(df3, x="score", color="score type", barmode="overlay", marginal="box",
                   title=t("Distribution of meta and user ratings",
                           "Distribution des notes méta et joueurs"))
st.plotly_chart(fig, use_container_width=True)

if len(d) > 10:
    fig = ff.create_distplot(
        [d["meta_score"].tolist(), d["n_user_score"].tolist()],
        [t("Meta score", "Note méta"), t("User score", "Note joueurs")],
        bin_size=1, show_hist=False, show_rug=False)
    fig.update_layout(title=t("Smoothed score distributions (KDE)",
                              "Distributions lissées (KDE)"))
    st.plotly_chart(fig, use_container_width=True)

fig = px.box(df3, x="score", y="platform", color="score type", hover_name="title",
             category_orders=CATEGORY_ORDERS,
             title=t("Score distributions per platform",
                     "Distributions des notes par plateforme"))
fig.update_layout(height=max(500, 60 * df3["platform"].nunique()))
st.plotly_chart(fig, use_container_width=True)

st.markdown(t(
    f"""
### {term("offset")} distribution

**{term("offset")}** = Metascore minus (-) user score, per game. The higher the offset,
the more the game is *overrated by critics* relative to users (negative offset → users
were more generous). The distribution leans right: more games are overrated by critics
than the other way around.
""",
    f"""
### Distribution de l'{term("offset")}

**{term("offset")}** = Metascore moins (-) note joueurs, par jeu. Plus l'offset est
grand, plus le jeu est *survalorisé par la critique* par rapport aux joueurs (offset
négatif → les joueurs ont été plus généreux). La distribution penche à droite : les
jeux survalorisés par la critique sont plus nombreux que l'inverse.
"""), unsafe_allow_html=True)

fig = px.histogram(d, x="offset", title=t("Offset distribution", "Distribution de l'offset"),
                   labels={"offset": t("Offset value", "Valeur de l'offset")})
fig.add_vline(x=0, line_color="red", line_width=1)
st.plotly_chart(fig, use_container_width=True)

st.markdown(t(
    f"""
### {term("ratio")} distribution

**{term("ratio")}** = number of user ratings ÷ number of critic reviews. A ratio of 1
means as many users rated the game as there were professional reviews. High ratios
flag games where users showed up *en masse* — often review bombing (or a passionate
fanbase).
""",
    f"""
### Distribution du {term("ratio")}

**{term("ratio")}** = nombre de notes joueurs ÷ nombre d'avis critiques. Un ratio de 1
signifie autant de joueurs votants que de critiques professionnelles. Les ratios élevés
signalent les jeux où les joueurs ont afflué *en masse* — souvent du review bombing
(ou une communauté passionnée).
"""), unsafe_allow_html=True)

r = d[d["ratio"].notna()]
if r.empty:
    st.info(t("Ratio requires user rating counts — run `scrape.py user-stats` to collect them.",
              "Le ratio nécessite les compteurs de notes joueurs — lancer `scrape.py user-stats`."))
else:
    st.metric(t("Average ratio", "Ratio moyen"), f"{r['ratio'].mean():.1f}")

    c_min, c_max = st.columns(2)
    with c_min:
        min_r = st.slider(t("Show ratio ≥", "Afficher ratio ≥"), 0, 100, 0,
                          help=t("Filter out low-ratio games", "Exclure les jeux à faible ratio"))
    with c_max:
        cap = st.slider(t("Clip ratio axis at", "Tronquer l'axe du ratio à"), 10, 500, 100)
    plot_r = r[(r["ratio"] >= min_r) & (r["ratio"] <= cap)]
    fig = px.histogram(plot_r, x="ratio",
                       title=t("Ratio distribution (log scale)",
                               "Distribution du ratio (échelle log)"))
    fig.update_xaxes(type="log")
    st.plotly_chart(fig, use_container_width=True)

    tmp = r.groupby("year")["ratio"].mean().reset_index()
    fig = px.line(tmp, x="year", y="ratio",
                  labels={"year": t("year", "année")},
                  title=t("Average ratio per year", "Ratio moyen par année"))
    st.plotly_chart(fig, use_container_width=True)

    tmp = r.groupby(["year", "platform"])["ratio"].mean().reset_index()
    fig = px.line(tmp, x="year", y="ratio", color="platform",
                  category_orders=CATEGORY_ORDERS,
                  labels={"year": t("year", "année")},
                  title=t("Average ratio per platform, per year",
                          "Ratio moyen par plateforme et par année"))
    st.plotly_chart(fig, use_container_width=True)
