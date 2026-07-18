"""
providers/pixabay_music.py

Pixabay — free commercial-use music + SFX, no attribution required.
Gives every episode fresh background music instead of the single static
gg_battle_theme.mp3.

Setup (30 seconds — see FREE_API_SETUP.md):
  https://pixabay.com/api/docs/ → free account → API key → PIXABAY_API_KEY in .env

Downloads are cached in music/pixabay/ so a track is fetched once and
reused across renders. All methods return a Path or None — never raise —
so empire_render.py can always fall back to the static theme.

[Likely] Pixabay's audio search rides the same key as the image/video API;
the endpoint + response fields have shifted over time, so this module tries
multiple endpoint and field shapes and fails soft to the static theme.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "music" / "pixabay"
MIN_AUDIO_BYTES = 100_000  # a real music track is at least ~100KB
LOG_TAG = "[pixabay_music]"

# Endpoint shapes tried in order (Pixabay has moved its audio API around).
SEARCH_URLS: tuple[str, ...] = (
    "https://pixabay.com/api/videos/music/?key={key}&q={query}&per_page=3&category={category}",
    "https://pixabay.com/api/audio/?key={key}&q={query}&per_page=3&category={category}",
)
# Field names that may hold the downloadable audio URL on a hit.
AUDIO_URL_FIELDS: tuple[str, ...] = ("audio", "audio_url", "download_url", "previewURL", "url")


def _load_env() -> None:
    """Populate os.environ from the repo-root .env (never overrides existing vars)."""
    env_path = str(BASE_DIR / ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _slug(text: str) -> str:
    """Filesystem-safe cache filename fragment."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60]


class PixabayMusicProvider:
    """Pixabay free music/SFX fetcher with local caching (music/pixabay/)."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("PIXABAY_API_KEY", "").strip()

    def is_connected(self) -> bool:
        """True if PIXABAY_API_KEY is set in .env."""
        return bool(self.api_key)

    # ── Internals ──────────────────────────────────────────────────────────
    def _search(self, query: str, category: str) -> list[dict]:
        """Search Pixabay audio; returns hits list (may be empty). Never raises."""
        for url_tpl in SEARCH_URLS:
            url = url_tpl.format(key=self.api_key,
                                 query=urllib.parse.quote(query),
                                 category=urllib.parse.quote(category))
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                hits = result.get("hits") or []
                if hits:
                    return hits
            except urllib.error.HTTPError as e:
                print(f"{LOG_TAG} search HTTP {e.code} at {url_tpl.split('?')[0]}",
                      flush=True)
            except Exception as e:
                print(f"{LOG_TAG} search failed: {e}", flush=True)
        return []

    @staticmethod
    def _extract_audio_url(hit: dict) -> str | None:
        """Pull the first plausible audio URL from a search hit."""
        for field in AUDIO_URL_FIELDS:
            value = hit.get(field)
            if isinstance(value, str) and value.startswith("http"):
                return value
        # Some shapes nest the file under hit["audios"]/hit["files"]
        for nest in ("audios", "files"):
            nested = hit.get(nest)
            if isinstance(nested, dict):
                for value in nested.values():
                    if isinstance(value, dict) and str(value.get("url", "")).startswith("http"):
                        return value["url"]
        return None

    def _download(self, url: str, dest: Path) -> Path | None:
        """Download an audio file to dest; validates size. Never raises."""
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if len(data) < MIN_AUDIO_BYTES:
                print(f"{LOG_TAG} download too small ({len(data)} bytes) — rejected",
                      flush=True)
                return None
            dest.write_bytes(data)
            print(f"{LOG_TAG} downloaded {dest.name} ({len(data) // 1024}KB)", flush=True)
            return dest
        except Exception as e:
            print(f"{LOG_TAG} download failed: {e}", flush=True)
            dest.unlink(missing_ok=True)
            return None

    def _fetch(self, query: str, category: str, cache_name: str) -> Path | None:
        """Cache-first fetch: return cached mp3 or search+download a new one."""
        cached = CACHE_DIR / f"{cache_name}.mp3"
        if cached.exists() and cached.stat().st_size > MIN_AUDIO_BYTES:
            print(f"{LOG_TAG} cache hit: {cached.name}", flush=True)
            return cached
        if not self.is_connected():
            return None
        for hit in self._search(query, category)[:3]:
            url = self._extract_audio_url(hit)
            if url and self._download(url, cached):
                return cached
        print(f"{LOG_TAG} no usable track for '{query}'", flush=True)
        return None

    # ── Public API ─────────────────────────────────────────────────────────
    def get_battle_music(self, episode_id: str) -> Path | None:
        """
        Epic orchestral battle track for a GG episode, cached per episode so
        every episode gets a consistent (but not identical-across-episodes)
        soundtrack. Returns mp3 path or None (caller falls back to static theme).
        """
        return self._fetch("epic battle orchestral", "music",
                           f"battle_{_slug(episode_id)}")

    def get_sfx(self, keyword: str) -> Path | None:
        """Fetch a sound effect by keyword. Returns mp3 path or None."""
        return self._fetch(keyword, "sound-effects", f"sfx_{_slug(keyword)}")
