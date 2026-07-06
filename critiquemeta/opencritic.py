"""Module OpenCritic (optionnel) — croise un échantillon de jeux avec OpenCritic.

Nécessite une clé RapidAPI (compte gratuit, quota limité) :
    https://rapidapi.com/opencritic-opencritic-default/api/opencritic-api

    export RAPIDAPI_KEY=...
    python -m critiquemeta.opencritic --top 300

Prend les N jeux Metacritic les plus commentés par la critique (sortis depuis 2015,
date de naissance d'OpenCritic), les cherche sur OpenCritic et enregistre
data/opencritic.csv. Reprend là où il s'est arrêté (raw_data/opencritic.jsonl) :
relancer la commande les jours suivants si le quota est épuisé.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_data"
DATA = ROOT / "data"

HOST = "opencritic-api.p.rapidapi.com"


def api_get(path, key, **params):
    url = f"https://{HOST}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "x-rapidapi-key": key,
        "x-rapidapi-host": HOST,
        "User-Agent": "CritiqueMeta/2.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def pick_sample(top):
    games = pd.read_parquet(DATA / "games.parquet")
    pool = games[(games["year"] >= 2015) & games["meta_score"].notna()]
    # un titre peut exister sur plusieurs plateformes : on garde la ligne la plus commentée
    pool = (pool.sort_values("meta_count", ascending=False)
            .drop_duplicates(subset=["title"])
            .head(top))
    return pool[["title", "slug", "meta_score", "user_score", "meta_count", "year"]]


def main():
    parser = argparse.ArgumentParser(description="Échantillon comparatif OpenCritic")
    parser.add_argument("--top", type=int, default=300,
                        help="nombre de jeux Metacritic à croiser (défaut 300)")
    parser.add_argument("--rate", type=float, default=1.0, help="requêtes/seconde")
    args = parser.parse_args()

    key = os.environ.get("RAPIDAPI_KEY")
    if not key:
        sys.exit("RAPIDAPI_KEY manquant. Créer une clé (gratuite) sur "
                 "https://rapidapi.com/opencritic-opencritic-default/api/opencritic-api "
                 "puis : export RAPIDAPI_KEY=...")

    RAW.mkdir(exist_ok=True)
    out = RAW / "opencritic.jsonl"
    done = set()
    if out.exists():
        with open(out) as f:
            done = {json.loads(l)["mc_slug"] for l in f if l.strip()}

    sample = pick_sample(args.top)
    todo = sample[~sample["slug"].isin(done)]
    print(f"{len(todo)} jeux à croiser ({len(done)} déjà faits)")

    n = 0
    with open(out, "a") as fh:
        for _, row in todo.iterrows():
            time.sleep(1.0 / args.rate)
            try:
                results = api_get("/game/search", key, criteria=row["title"])
                if not results:
                    fh.write(json.dumps({"mc_slug": row["slug"], "match": None}) + "\n")
                    continue
                best = results[0]
                game = api_get(f"/game/{best['id']}", key)
                fh.write(json.dumps({
                    "mc_slug": row["slug"],
                    "mc_title": row["title"],
                    "match": best.get("name"),
                    "match_dist": best.get("dist"),
                    "oc_id": game.get("id"),
                    "oc_score": game.get("topCriticScore"),
                    "oc_median": game.get("medianScore"),
                    "oc_tier": game.get("tier"),
                    "oc_num_reviews": game.get("numReviews"),
                    "oc_percent_recommended": game.get("percentRecommended"),
                    "oc_release": game.get("firstReleaseDate"),
                }, ensure_ascii=False) + "\n")
                fh.flush()
                n += 1
                if n % 25 == 0:
                    print(f"{n}/{len(todo)}")
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"Quota RapidAPI épuisé après {n} jeux — relancer plus tard, "
                          "la collecte reprendra ici.")
                    break
                print(f"{row['title']}: HTTP {e.code}, ignoré")

    # export CSV consolidé
    rows = [json.loads(l) for l in open(out) if l.strip()]
    df = pd.DataFrame([r for r in rows if r.get("match")])
    if not df.empty:
        # écarte les correspondances de titre douteuses (distance de Levenshtein normalisée)
        df = df[df["match_dist"].fillna(1) <= 0.35]
        df.to_csv(DATA / "opencritic.csv", index=False)
        print(f"data/opencritic.csv : {len(df)} jeux croisés")


if __name__ == "__main__":
    main()
