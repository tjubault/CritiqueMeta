"""Client pour l'API JSON interne de Metacritic (backend.metacritic.com).

Cette API est celle qu'utilise le frontend metacritic.com (app Nuxt/Fandom).
La clé ci-dessous est la clé publique embarquée dans le frontend.
Usage poli : rate-limit par défaut ~3 req/s, backoff sur 429/5xx.
"""

import json
import os
import random
import threading
import time
import urllib.parse
import urllib.request
import urllib.error

API_ROOT = "https://backend.metacritic.com"
API_KEY = os.environ.get("MC_API_KEY", "1MOZgmNFxvmljaQR1X9KAij9Mo4xAY3u")

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

# slug -> id, découverts via /games/metacritic/{slug}/web (champ platforms[].id)
PLATFORMS = {
    "pc": 1500000019,
    "dreamcast": 1500000067,
    "playstation": 1500000078,
    "nintendo-64": 1500000084,
    "game-boy-advance": 1500000091,
    "playstation-2": 1500000094,
    "xbox": 1500000098,
    "gamecube": 1500000099,
    "ds": 1500000108,
    "psp": 1500000109,
    "xbox-360": 1500000111,
    "ios-iphoneipad": 1500000112,
    "playstation-3": 1500000113,
    "wii": 1500000114,
    "3ds": 1500000116,
    "playstation-vita": 1500000117,
    "wii-u": 1500000118,
    "playstation-4": 1500000120,
    "xbox-one": 1500000121,
    "nintendo-switch": 1500000124,
    "meta-quest": 1500000127,
    "playstation-5": 1500000128,
    "xbox-series-x": 1500000129,
    "nintendo-switch-2": 1500000154,
}

PLATFORM_NAMES = {
    "pc": "PC",
    "dreamcast": "Dreamcast",
    "playstation": "PlayStation",
    "nintendo-64": "Nintendo 64",
    "game-boy-advance": "Game Boy Advance",
    "playstation-2": "PlayStation 2",
    "xbox": "Xbox",
    "gamecube": "GameCube",
    "ds": "DS",
    "psp": "PSP",
    "xbox-360": "Xbox 360",
    "ios-iphoneipad": "iOS (iPhone/iPad)",
    "playstation-3": "PlayStation 3",
    "wii": "Wii",
    "3ds": "3DS",
    "playstation-vita": "PlayStation Vita",
    "wii-u": "Wii U",
    "playstation-4": "PlayStation 4",
    "xbox-one": "Xbox One",
    "nintendo-switch": "Nintendo Switch",
    "meta-quest": "Meta Quest",
    "playstation-5": "PlayStation 5",
    "xbox-series-x": "Xbox Series X",
    "nintendo-switch-2": "Nintendo Switch 2",
}

# Tailles de page maximales observées (l'API clampe ou renvoie 400 au-delà)
FINDER_PAGE_SIZE = 50
CRITIC_REVIEWS_PAGE_SIZE = 10
USER_REVIEWS_PAGE_SIZE = 300


class MCClient:
    def __init__(self, rate=3.0, max_retries=5, timeout=30):
        self.min_interval = 1.0 / rate
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_request = 0.0
        self.request_count = 0
        self._lock = threading.Lock()

    def _throttle(self):
        # partagé entre threads : réserve le prochain créneau puis attend son tour
        with self._lock:
            now = time.monotonic()
            slot = max(self._last_request + self.min_interval, now)
            self._last_request = slot
        wait = slot - time.monotonic()
        if wait > 0:
            time.sleep(wait)

    def get(self, path, **params):
        """GET {API_ROOT}{path} avec apiKey, retries et rate-limit. Renvoie le JSON parsé.

        Lève urllib.error.HTTPError sur 4xx définitif (ex : 404 fiche disparue).
        """
        params["apiKey"] = API_KEY
        url = f"{API_ROOT}{path}?{urllib.parse.urlencode(params)}"
        last_err = None
        for attempt in range(self.max_retries):
            self._throttle()
            req = urllib.request.Request(url, headers={"User-Agent": random.choice(USER_AGENTS)})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    self.request_count += 1
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504):
                    last_err = e
                    time.sleep(min(2 ** attempt * 2, 60))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
                last_err = e
                time.sleep(min(2 ** attempt * 2, 60))
        raise RuntimeError(f"Échec après {self.max_retries} tentatives : {url}") from last_err

    # ---- endpoints ----

    def finder_page(self, platform_id, offset, limit=FINDER_PAGE_SIZE, sort="-releaseDate"):
        return self.get(
            "/finder/metacritic/web",
            productType="games",
            gamePlatformIds=platform_id,
            sortBy=sort,
            offset=offset,
            limit=limit,
        )["data"]

    def game_detail(self, slug):
        return self.get(f"/games/metacritic/{slug}/web")["data"]["item"]

    def user_stats(self, slug, platform_slug):
        return self.get(
            f"/reviews/metacritic/user/games/{slug}/platform/{platform_slug}/stats/web"
        )["data"]["item"]

    def critic_reviews_page(self, slug, platform_slug, offset, limit=CRITIC_REVIEWS_PAGE_SIZE):
        return self.get(
            f"/reviews/metacritic/critic/games/{slug}/platform/{platform_slug}/web",
            offset=offset,
            limit=limit,
        )["data"]

    def user_reviews_page(self, slug, platform_slug, offset, limit=USER_REVIEWS_PAGE_SIZE):
        return self.get(
            f"/reviews/metacritic/user/games/{slug}/platform/{platform_slug}/web",
            offset=offset,
            limit=limit,
        )["data"]
