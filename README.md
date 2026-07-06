# CritiqueMeta

CritiqueMeta collects video-game rating data and explores the biases between
professional critics and players: are users getting tougher? are ratings constantly
increasing? what drives user dissatisfaction?

**v2 (2026)** — the project was rebuilt around Metacritic's JSON API (the HTML
scraper died with the 2023 site redesign) and the analysis moved from a static
notebook export to an interactive **Streamlit app**. Coverage grew from 7 consoles
(2012–2023) to the **entire Metacritic catalog** — every platform, PC included.

## Architecture

```
critiquemeta/          collection & preparation CLIs
  mc_client.py         Metacritic API client (rate-limited, retries)
  scrape.py            data collection, incremental & resumable
  clean.py             raw JSONL -> analysis-ready parquet/CSV
  opencritic.py        optional OpenCritic comparison sample (RapidAPI key)
app/                   Streamlit app (one page per theme)
raw_data/              scraping checkpoints (JSONL, git-ignored) + legacy 2023 CSVs
data/                  cleaned datasets (parquet)
legacy/                v1 notebooks and the old HTML report
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 1 — Collect

All commands are incremental: interrupt them freely, re-run to resume.

```bash
python -m critiquemeta.scrape catalog        # full per-platform catalog (~500k rows, ~1h)
python -m critiquemeta.scrape details        # developer/publisher for every rated title
python -m critiquemeta.scrape user-stats     # user rating counts per (title, platform)
python -m critiquemeta.scrape reviews-critic # individual critic reviews (long!)
python -m critiquemeta.scrape reviews-user   # individual user reviews, capped per game
python -m critiquemeta.scrape status         # progress overview
```

Useful flags: `--platform playstation-5` (restrict), `--limit N` (smoke test),
`--rate` / `--workers` (throughput, keep it polite), `--max-per-game` /
`--full` (user review depth).

> The collection uses `backend.metacritic.com`, the JSON API behind metacritic.com,
> with the site's own public API key. Intended for personal / research use — keep the
> default rate limits reasonable.

## 2 — Clean

```bash
python -m critiquemeta.clean
```

Produces `data/games.parquet` (one row per title-platform, with derived columns:
`offset` = Metascore − user score, `ratio` = user ratings / critic reviews, …),
`data/meta_reviews.parquet` and `data/user_reviews.parquet`.

## 3 — Explore

```bash
streamlit run app/Accueil.py
```

Pages: score distributions, platform view, game-by-game scatter & explorer,
critic-publication biases, developers, time trends, and an optional
Metacritic-vs-OpenCritic comparison.

## Optional — OpenCritic

Create a free key on [RapidAPI (OpenCritic API)](https://rapidapi.com/opencritic-opencritic-default/api/opencritic-api), then:

```bash
export RAPIDAPI_KEY=...
python -m critiquemeta.opencritic --top 300
```

The free quota is small; the script checkpoints and resumes across days. Once
`data/opencritic.csv` exists, the OpenCritic page of the app lights up.

## Deploying the app

The repo is directly deployable on [Streamlit Community Cloud](https://share.streamlit.io):
point it at `app/Accueil.py`. The parquet datasets in `data/` are versioned so the
cloud app works without re-scraping.
