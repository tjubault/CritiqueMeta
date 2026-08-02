"""Chargement des données, i18n et filtres partagés par toutes les pages de l'app."""

from pathlib import Path

import pandas as pd
import plotly.io as pio
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"

pio.templates.default = "plotly_dark"

# Ordre chronologique (approximatif) pour les légendes
PLATFORM_ORDER = [
    "PlayStation", "Nintendo 64", "Dreamcast", "PlayStation 2", "Game Boy Advance",
    "GameCube", "Xbox", "DS", "PSP", "Xbox 360", "Wii", "PlayStation 3",
    "iOS (iPhone/iPad)", "3DS", "PlayStation Vita", "Wii U", "PlayStation 4",
    "Xbox One", "PC", "Nintendo Switch", "Meta Quest", "PlayStation 5",
    "Xbox Series X", "Nintendo Switch 2",
]

CATEGORY_ORDERS = {"platform": PLATFORM_ORDER, "score type": ["meta", "user"]}


# --------------------------------------------------------------------------- i18n

def t(en, fr):
    """Renvoie la chaîne dans la langue active (anglais par défaut)."""
    return fr if st.session_state.get("lang") == "fr" else en


def lang_selector():
    """Drapeau en haut à droite pour basculer la langue de toute l'app."""
    _, col = st.columns([10, 1])
    with col:
        if st.session_state.get("lang") == "fr":
            if st.button("🇬🇧 EN", help="Switch to English"):
                st.session_state["lang"] = "en"
                st.rerun()
        else:
            if st.button("🇫🇷 FR", help="Passer en français"):
                st.session_state["lang"] = "fr"
                st.rerun()


# --------------------------------------------------------------------------- glossaire

def glossary_css():
    """Injecte le style des termes du glossaire (couleur + italique + info-bulle)."""
    st.markdown(
        """
<style>
.glossary-term {
    color: #4fc3f7;
    font-style: italic;
    cursor: help;
    border-bottom: 1px dotted #4fc3f7;
}
</style>
""",
        unsafe_allow_html=True)


_TERMS = {
    "metascore": {
        "label": ("Metascore", "Metascore"),
        "def": ("Weighted average of professional critic reviews (0-100).",
                "Moyenne pondérée des critiques professionnelles (0-100)."),
    },
    "user_score": {
        "label": ("User score", "Note joueurs"),
        "def": ("Average of user ratings (0-10, shown x10 to match the Metascore scale).",
                "Moyenne des notes des joueurs (0-10, affichée x10 pour être comparable "
                "au Metascore)."),
    },
    "offset": {
        "label": ("Offset", "Offset"),
        "def": ("Metascore minus (-) user score.",
                "Metascore moins (-) note joueurs."),
    },
    "ratio": {
        "label": ("Ratio", "Ratio"),
        "def": ("(Number of user ratings) divided by (number of critic reviews).",
                "(Nombre de notes joueurs) divisé par (nombre d'avis critique pro)."),
    },
}


def term(key, label=None):
    """Span coloré + italique avec la définition du terme affichée au survol."""
    spec = _TERMS[key]
    label = label if label is not None else t(*spec["label"])
    definition = t(*spec["def"])
    return f'<span class="glossary-term" title="{definition}">{label}</span>'


# --------------------------------------------------------------------------- data

@st.cache_data(show_spinner="Loading dataset…")
def _load_games(mtime):
    df = pd.read_parquet(DATA / "games.parquet")
    df["genres"] = df["genres"].apply(list)
    return df


def load_games():
    # le mtime sert de clé de cache : un nouveau clean invalide automatiquement
    return _load_games((DATA / "games.parquet").stat().st_mtime)


@st.cache_data(show_spinner=False)
def _load_reviews(kind, mtime):
    return pd.read_parquet(DATA / f"{kind}.parquet")


def load_reviews(kind):
    """kind: 'meta_reviews' ou 'user_reviews'. DataFrame vide si absent."""
    path = DATA / f"{kind}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return _load_reviews(kind, path.stat().st_mtime)


# --------------------------------------------------------------------------- UI partagée

def sidebar_filters(df, key_prefix=""):
    """Filtres communs en sidebar. Renvoie le df filtré."""
    st.sidebar.header(t("Filters", "Filtres"))

    platforms = sorted(df["platform"].unique(), key=lambda p: PLATFORM_ORDER.index(p)
                       if p in PLATFORM_ORDER else 99)
    if st.sidebar.button(t("Select all platforms", "Toutes les plateformes"),
                         key=f"{key_prefix}all_platforms"):
        st.session_state[f"{key_prefix}platforms"] = platforms
    chosen = st.sidebar.multiselect(t("Platforms", "Plateformes"), platforms,
                                    default=platforms, key=f"{key_prefix}platforms")

    years = df["year"].dropna()
    y_min, y_max = int(years.min()), int(years.max())
    y_range = st.sidebar.slider(t("Release year", "Année de sortie"), y_min, y_max,
                                (y_min, y_max), key=f"{key_prefix}years")

    min_critics = st.sidebar.slider(
        t("Min. critic reviews", "Min. d'avis critiques"), 0, 30, 10,
        key=f"{key_prefix}mincritics",
        help=t("Keep games with at least N critic reviews",
               "Ne garder que les jeux ayant au moins N avis critiques"))

    out = df[df["platform"].isin(chosen)
             & df["year"].between(*y_range)]
    if min_critics:
        out = out[out["meta_count"] >= min_critics]
    return out


def scored(df):
    """Jeux ayant à la fois un score critique et un score utilisateur."""
    return df[df["meta_score"].notna() & df["n_user_score"].notna()]


def long_scores(df):
    """Format long : une ligne par (jeu, type de score) — équivalent df_games3."""
    d = scored(df)
    meta = d.assign(score=d["meta_score"], **{"score type": "meta"})
    user = d.assign(score=d["n_user_score"], **{"score type": "user"})
    return pd.concat([meta, user], ignore_index=True)


def dataset_caption(df):
    d = scored(df)
    st.caption(t(
        f"{len(df):,} title-platform entries match the current filters — "
        f"{len(d):,} have both a Metascore and a user score.",
        f"{len(df):,} entrées titre-plateforme correspondent aux filtres — "
        f"{len(d):,} ont à la fois un Metascore et une note utilisateur."
    ))
