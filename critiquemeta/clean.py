"""Nettoyage : JSONL bruts (raw_data/) -> datasets analysables (data/).

    python -m critiquemeta.clean

Produit :
    data/games.parquet         une ligne par (titre, plateforme), colonnes dérivées incluses
    data/meta_reviews.parquet  un avis critique individuel par ligne
    data/user_reviews.parquet  un avis utilisateur individuel par ligne
    + les mêmes en CSV pour compatibilité.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_data"
DATA = ROOT / "data"


def read_jsonl(path):
    rows = []
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return pd.DataFrame(rows)


def build_games():
    frames = [read_jsonl(f) for f in sorted(RAW.glob("catalog_*.jsonl"))]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise SystemExit("Aucun catalog_*.jsonl dans raw_data/ — lancer scrape.py catalog d'abord.")
    games = pd.concat(frames, ignore_index=True)
    games = games.drop_duplicates(subset=["slug", "platform_slug"], keep="last")

    # compteurs d'avis utilisateurs (scrape user-stats)
    stats = read_jsonl(RAW / "user_stats.jsonl")
    if not stats.empty:
        stats = stats[stats.get("error").isna()] if "error" in stats else stats
        stats = stats.drop_duplicates(subset=["slug", "platform_slug"], keep="last")
        stats = stats[["slug", "platform_slug", "user_count", "user_pos", "user_mixed", "user_neg"]]
        games = games.merge(stats, on=["slug", "platform_slug"], how="left")
    else:
        games[["user_count", "user_pos", "user_mixed", "user_neg"]] = pd.NA

    # développeur / éditeur (scrape details)
    details = read_jsonl(RAW / "details.jsonl")
    if not details.empty:
        details = details[details.get("error").isna()] if "error" in details else details
        details = details.drop_duplicates(subset=["slug"], keep="last")
        details["developer"] = details["developers"].apply(lambda d: d[0] if isinstance(d, list) and d else None)
        details["publisher"] = details["publishers"].apply(lambda p: p[0] if isinstance(p, list) and p else None)
        games = games.merge(
            details[["slug", "developer", "publisher", "must_play"]], on="slug", how="left"
        )
    else:
        games[["developer", "publisher", "must_play"]] = pd.NA

    # types et colonnes dérivées
    games["release_date"] = pd.to_datetime(games["release_date"], errors="coerce")
    games = games.dropna(subset=["release_date", "title"])
    games["year"] = games["release_date"].dt.year
    games["month"] = games["release_date"].dt.month
    games["first_release"] = games.groupby("title")["release_date"].transform("min")

    for col in ["meta_score", "meta_count", "meta_pos", "meta_mixed", "meta_neg",
                "user_score", "user_count", "user_pos", "user_mixed", "user_neg"]:
        games[col] = pd.to_numeric(games[col], errors="coerce")

    games["n_user_score"] = games["user_score"] * 10
    games["offset"] = games["meta_score"] - games["n_user_score"]
    games["ratio"] = games["user_count"] / games["meta_count"].where(games["meta_count"] > 0)

    return games.reset_index(drop=True)


def build_reviews(kind, games):
    df = read_jsonl(RAW / f"{kind}_reviews.jsonl")
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df = df.dropna(subset=["score"])
    if kind == "user":
        df["score"] = df["score"] * 10  # même échelle 0-100 que les critiques
    lookup = games[["slug", "platform_slug", "title", "platform"]].drop_duplicates(["slug", "platform_slug"])
    df = df.merge(lookup, on=["slug", "platform_slug"], how="left")
    return df.reset_index(drop=True)


def main():
    DATA.mkdir(exist_ok=True)

    games = build_games()
    n_scored = int((games["meta_score"].notna() & games["n_user_score"].notna()).sum())
    print(f"games : {len(games)} lignes titre-plateforme, dont {n_scored} avec double score")
    games.to_parquet(DATA / "games.parquet", index=False)
    games_csv = games.copy()
    games_csv["genres"] = games_csv["genres"].apply(
        lambda g: "|".join(g) if isinstance(g, list) else "")
    games_csv.to_csv(DATA / "games.csv", index=False)

    for kind, out in [("critic", "meta_reviews"), ("user", "user_reviews")]:
        df = build_reviews(kind, games)
        print(f"{out} : {len(df)} avis")
        if not df.empty:
            df.to_parquet(DATA / f"{out}.parquet", index=False)
            df.to_csv(DATA / f"{out}.csv", index=False)

    # contrôles d'intégrité
    assert games["meta_score"].dropna().between(0, 100).all(), "meta_score hors bornes"
    assert games["user_score"].dropna().between(0, 10).all(), "user_score hors bornes"
    assert not games.duplicated(["slug", "platform_slug"]).any(), "doublons titre-plateforme"
    print("contrôles d'intégrité : OK")


if __name__ == "__main__":
    main()
