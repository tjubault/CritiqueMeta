"""CLI de collecte Metacritic. Toutes les étapes sont incrémentales et reprennent
là où elles se sont arrêtées (checkpoints dans raw_data/).

Étapes, dans l'ordre :
    python -m critiquemeta.scrape catalog        # catalogue complet par plateforme (finder)
    python -m critiquemeta.scrape details        # fiche par titre noté (développeur, éditeur, rating)
    python -m critiquemeta.scrape user-stats     # compteurs d'avis utilisateurs par (titre, plateforme)
    python -m critiquemeta.scrape reviews-critic # avis critiques individuels (pagination complète)
    python -m critiquemeta.scrape reviews-user   # avis utilisateurs individuels (plafonnés par jeu)

`status` affiche l'avancement et les volumes restants.
"""

import argparse
import json
import sys
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .mc_client import (
    MCClient,
    PLATFORMS,
    PLATFORM_NAMES,
    FINDER_PAGE_SIZE,
    CRITIC_REVIEWS_PAGE_SIZE,
    USER_REVIEWS_PAGE_SIZE,
)

RAW = Path(__file__).resolve().parent.parent / "raw_data"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def count_lines(path):
    if not path.exists():
        return 0
    with open(path) as f:
        return sum(1 for _ in f)


def iter_jsonl(path):
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def append_jsonl(fh, obj):
    fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- catalog

def slim_finder_item(item, platform_slug):
    css = item.get("criticScoreSummary") or {}
    return {
        "mc_id": item.get("id"),
        "title": item.get("title"),
        "slug": item.get("slug"),
        "platform": PLATFORM_NAMES[platform_slug],
        "platform_slug": platform_slug,
        "release_date": item.get("releaseDate"),
        "premiere_year": item.get("premiereYear"),
        "rating": item.get("rating"),
        "genres": [g["name"] for g in item.get("genres") or [] if g.get("name")],
        "meta_score": css.get("score"),
        "meta_count": css.get("reviewCount"),
        "meta_pos": css.get("positiveCount"),
        "meta_mixed": css.get("neutralCount"),
        "meta_neg": css.get("negativeCount"),
        "user_score": (item.get("userScore") or {}).get("score"),
    }


def cmd_catalog(client, args):
    platforms = args.platform or list(PLATFORMS)
    for pslug in platforms:
        pid = PLATFORMS[pslug]
        out = RAW / f"catalog_{pslug}.jsonl"
        done_marker = RAW / f"catalog_{pslug}.complete"
        if done_marker.exists() and not args.restart:
            log(f"{pslug}: déjà complet, ignoré (supprimer {done_marker.name} pour re-scraper)")
            continue
        start = count_lines(out)
        page = client.finder_page(pid, 0, limit=1)
        total = page["totalResults"]
        log(f"{pslug}: {total} jeux, reprise à l'offset {start}")
        offsets = list(range(start, total, FINDER_PAGE_SIZE))
        if args.limit:
            offsets = [o for o in offsets if o < args.limit]
        written = start
        # fetch parallèle mais écriture dans l'ordre des offsets (le resume
        # suppose un fichier contigu) ; executor.map préserve l'ordre
        with open(out, "a") as fh, ThreadPoolExecutor(args.workers) as pool:
            for data in pool.map(lambda o: client.finder_page(pid, o), offsets):
                for item in data["items"]:
                    append_jsonl(fh, slim_finder_item(item, pslug))
                written += len(data["items"])
                if written % 5000 < FINDER_PAGE_SIZE:
                    log(f"{pslug}: {written}/{total}")
        if args.limit:
            log(f"{pslug}: --limit atteint ({written} lignes)")
            return
        done_marker.touch()
        log(f"{pslug}: terminé ({written} lignes)")


# --------------------------------------------------------------------------- helpers de sélection

def scored_rows():
    """Toutes les lignes du catalogue ayant un score critique ou utilisateur.

    Dédoublonnées par (slug, platform_slug).
    """
    seen = set()
    rows = []
    for f in sorted(RAW.glob("catalog_*.jsonl")):
        for row in iter_jsonl(f):
            if row.get("meta_score") is None and row.get("user_score") is None:
                continue
            key = (row["slug"], row["platform_slug"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows


def load_done(path):
    if not path.exists():
        return set()
    with open(path) as f:
        return {tuple(line.strip().split("\t")) for line in f if line.strip()}


# --------------------------------------------------------------------------- details

def cmd_details(client, args):
    out = RAW / "details.jsonl"
    done = {row["slug"] for row in iter_jsonl(out)}
    slugs = []
    seen = set()
    for row in scored_rows():
        if row["slug"] not in seen:
            seen.add(row["slug"])
            if row["slug"] not in done:
                slugs.append(row["slug"])
    if args.limit:
        slugs = slugs[:args.limit]
    log(f"details: {len(slugs)} titres à récupérer ({len(done)} déjà faits)")

    def fetch(slug):
        try:
            item = client.game_detail(slug)
        except urllib.error.HTTPError as e:
            return {"slug": slug, "error": e.code}
        companies = (item.get("production") or {}).get("companies") or []
        return {
            "slug": slug,
            "title": item.get("title"),
            "developers": [c["name"] for c in companies if c.get("typeName") == "Developer"],
            "publishers": [c["name"] for c in companies if c.get("typeName") == "Publisher"],
            "rating": item.get("rating"),
            "must_play": item.get("mustPlay"),
            "genres": [g["name"] for g in item.get("genres") or [] if g.get("name")],
        }

    n = 0
    with open(out, "a") as fh, ThreadPoolExecutor(args.workers) as pool:
        for rec in pool.map(fetch, slugs):
            append_jsonl(fh, rec)
            n += 1
            if n % 500 == 0:
                log(f"details: {n}/{len(slugs)}")
    log(f"details: terminé ({n} nouveaux)")


# --------------------------------------------------------------------------- user-stats

def cmd_user_stats(client, args):
    out = RAW / "user_stats.jsonl"
    done = {(r["slug"], r["platform_slug"]) for r in iter_jsonl(out)}
    pairs = [
        (r["slug"], r["platform_slug"])
        for r in scored_rows()
        if r.get("user_score") is not None and (r["slug"], r["platform_slug"]) not in done
    ]
    if args.limit:
        pairs = pairs[:args.limit]
    log(f"user-stats: {len(pairs)} paires à récupérer ({len(done)} déjà faites)")

    def fetch(pair):
        slug, pslug = pair
        try:
            item = client.user_stats(slug, pslug)
        except urllib.error.HTTPError as e:
            return {"slug": slug, "platform_slug": pslug, "error": e.code}
        return {
            "slug": slug,
            "platform_slug": pslug,
            "user_score": item.get("score"),
            "user_count": item.get("reviewCount"),
            "user_pos": item.get("positiveCount"),
            "user_mixed": item.get("neutralCount"),
            "user_neg": item.get("negativeCount"),
        }

    n = 0
    with open(out, "a") as fh, ThreadPoolExecutor(args.workers) as pool:
        for rec in pool.map(fetch, pairs):
            append_jsonl(fh, rec)
            n += 1
            if n % 500 == 0:
                log(f"user-stats: {n}/{len(pairs)}")
    log(f"user-stats: terminé ({n} nouvelles)")


# --------------------------------------------------------------------------- reviews

def slim_critic_review(rev, slug, pslug):
    return {
        "slug": slug,
        "platform_slug": pslug,
        "critic": rev.get("publicationName"),
        "author": rev.get("author") or None,
        "score": rev.get("score"),
        "date": rev.get("date"),
    }


def slim_user_review(rev, slug, pslug):
    return {
        "slug": slug,
        "platform_slug": pslug,
        "user": rev.get("author"),
        "score": rev.get("score"),
        "date": rev.get("date"),
    }


def _scrape_reviews(client, args, kind):
    """kind = 'critic' ou 'user'."""
    out = RAW / f"{kind}_reviews.jsonl"
    done_file = RAW / f"{kind}_reviews.done"
    done = load_done(done_file)

    if kind == "critic":
        pairs = [
            (r["slug"], r["platform_slug"], r.get("meta_count") or 0)
            for r in scored_rows()
            if (r.get("meta_count") or 0) > 0
        ]
        page_size, slim, fetch = CRITIC_REVIEWS_PAGE_SIZE, slim_critic_review, client.critic_reviews_page
        cap = None
    else:
        pairs = [
            (r["slug"], r["platform_slug"], r.get("user_count") or 1)
            for r in iter_jsonl(RAW / "user_stats.jsonl")
            if not r.get("error") and (r.get("user_count") or 0) > 0
        ]
        page_size, slim, fetch = USER_REVIEWS_PAGE_SIZE, slim_user_review, client.user_reviews_page
        cap = None if args.full else args.max_per_game

    if args.platform:
        pairs = [p for p in pairs if p[1] in args.platform]
    todo = [p for p in pairs if (p[0], p[1]) not in done]
    if args.limit:
        todo = todo[:args.limit]
    log(f"reviews-{kind}: {len(todo)} paires à traiter ({len(done)} déjà faites)")

    def fetch_pair(pair):
        """Récupère toutes les pages d'une paire ; renvoie la liste d'avis."""
        slug, pslug, expected = pair
        revs = []
        offset = 0
        target = expected if cap is None else min(expected, cap)
        try:
            while offset < target:
                data = fetch(slug, pslug, offset, limit=min(page_size, target - offset))
                items = data.get("items") or []
                if not items:
                    break
                revs.extend(slim(rev, slug, pslug) for rev in items)
                offset += len(items)
                total = data.get("totalResults") or 0
                target = total if cap is None else min(total, cap)
        except urllib.error.HTTPError as e:
            log(f"reviews-{kind}: {slug}/{pslug} -> HTTP {e.code}, ignoré")
        return slug, pslug, revs

    n_pairs = 0
    with open(out, "a") as fh, open(done_file, "a") as dfh, \
            ThreadPoolExecutor(args.workers) as pool:
        for slug, pslug, revs in pool.map(fetch_pair, todo):
            for rec in revs:
                append_jsonl(fh, rec)
            dfh.write(f"{slug}\t{pslug}\n")
            dfh.flush()
            n_pairs += 1
            if n_pairs % 200 == 0:
                log(f"reviews-{kind}: {n_pairs}/{len(todo)} paires ({client.request_count} requêtes)")
    log(f"reviews-{kind}: terminé ({n_pairs} paires)")


# --------------------------------------------------------------------------- status

def cmd_status(client, args):
    total = 0
    for pslug in PLATFORMS:
        f = RAW / f"catalog_{pslug}.jsonl"
        n = count_lines(f)
        total += n
        flag = "✓" if (RAW / f"catalog_{pslug}.complete").exists() else ("…" if n else " ")
        print(f"  catalog {pslug:<20} {flag} {n}")
    print(f"  catalogue total : {total} lignes")
    rows = scored_rows()
    n_critic = sum(1 for r in rows if (r.get("meta_count") or 0) > 0)
    n_user = sum(1 for r in rows if r.get("user_score") is not None)
    print(f"  paires notées : {len(rows)} (critique : {n_critic}, user : {n_user})")
    print(f"  details        : {count_lines(RAW / 'details.jsonl')} titres")
    print(f"  user-stats     : {count_lines(RAW / 'user_stats.jsonl')} paires")
    print(f"  critic reviews : {count_lines(RAW / 'critic_reviews.jsonl')} avis "
          f"({len(load_done(RAW / 'critic_reviews.done'))} paires finies)")
    print(f"  user reviews   : {count_lines(RAW / 'user_reviews.jsonl')} avis "
          f"({len(load_done(RAW / 'user_reviews.done'))} paires finies)")


# --------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description="Collecte des données Metacritic")
    parser.add_argument("command", choices=["catalog", "details", "user-stats",
                                            "reviews-critic", "reviews-user", "status"])
    parser.add_argument("--platform", action="append", choices=list(PLATFORMS),
                        help="restreindre à une ou plusieurs plateformes")
    parser.add_argument("--limit", type=int, help="arrêt après N éléments (tests)")
    parser.add_argument("--rate", type=float, default=3.0, help="requêtes/seconde (défaut 3)")
    parser.add_argument("--workers", type=int, default=4,
                        help="requêtes en parallèle, bornées par --rate (défaut 4)")
    parser.add_argument("--max-per-game", type=int, default=200,
                        help="plafond d'avis utilisateurs par jeu (défaut 200)")
    parser.add_argument("--full", action="store_true", help="pas de plafond pour reviews-user")
    parser.add_argument("--restart", action="store_true", help="re-scraper même si marqué complet")
    args = parser.parse_args()

    RAW.mkdir(exist_ok=True)
    client = MCClient(rate=args.rate)
    t0 = time.time()
    try:
        if args.command == "catalog":
            cmd_catalog(client, args)
        elif args.command == "details":
            cmd_details(client, args)
        elif args.command == "user-stats":
            cmd_user_stats(client, args)
        elif args.command == "reviews-critic":
            _scrape_reviews(client, args, "critic")
        elif args.command == "reviews-user":
            _scrape_reviews(client, args, "user")
        elif args.command == "status":
            cmd_status(client, args)
    except KeyboardInterrupt:
        log("interrompu — relancer la même commande pour reprendre")
        sys.exit(130)
    finally:
        log(f"{client.request_count} requêtes en {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
