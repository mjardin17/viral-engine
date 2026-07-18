"""
providers/freepd_music.py

FreePD.com — 100% public-domain music, direct MP3 links, ZERO SIGNUP,
ZERO KEY. Replaces the single static gg_battle_theme.mp3 with per-episode
variety at zero cost and zero licensing risk.

Tracks are downloaded once into music/freepd/ and cached permanently.
select_track(episode_id) picks deterministically (hash of the episode id)
so re-renders of the same episode always get the same soundtrack.

All methods fail soft (return None) — empire_render.py falls back to the
static theme when this returns None.
"""

from __future__ import annotations

import hashlib
import threading
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "music" / "freepd"
MIN_AUDIO_BYTES = 100_000  # a real music track is at least ~100KB
LOG_TAG = "[freepd_music]"
UA = {"User-Agent": "EmpireOS/1.0"}

# Real FreePD battle/epic tracks (public domain, direct MP3 links).
TRACKS: tuple[str, ...] = (
    "https://freepd.com/music/Strength%20of%20the%20Titans.mp3",
    "https://freepd.com/music/Redline.mp3",
    "https://freepd.com/music/Dragon%20and%20Toast.mp3",
    "https://freepd.com/music/Epic%20Unease.mp3",
    "https://freepd.com/music/Sovereign.mp3",
)


def _track_filename(url: str) -> str:
    """'…/Strength%20of%20the%20Titans.mp3' → 'strength_of_the_titans.mp3'."""
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    return name.lower().replace(" ", "_")


def _episode_index(episode_id: str) -> int:
    """Stable track index for an episode (md5, not hash() — seed-independent)."""
    digest = hashlib.md5(episode_id.upper().encode("utf-8")).hexdigest()
    return int(digest, 16) % len(TRACKS)


class FreePDMusicProvider:
    """FreePD public-domain music with permanent local caching (music/freepd/)."""

    def is_connected(self) -> bool:
        """Always True — no key, no account, no signup."""
        return True

    # ── Internals ──────────────────────────────────────────────────────────
    def _download(self, url: str, dest: Path) -> Path | None:
        """Download one track; validates size. Never raises."""
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
            if len(data) < MIN_AUDIO_BYTES:
                print(f"{LOG_TAG} {dest.name} too small ({len(data)} bytes) — rejected",
                      flush=True)
                return None
            dest.write_bytes(data)
            print(f"{LOG_TAG} downloaded {dest.name} ({len(data) // 1024}KB)", flush=True)
            return dest
        except Exception as e:
            print(f"{LOG_TAG} download failed ({dest.name}): {e}", flush=True)
            dest.unlink(missing_ok=True)
            return None

    # ── Public API ─────────────────────────────────────────────────────────
    def get_cached_track(self, episode_id: str) -> Path | None:
        """
        Cache-only lookup: this episode's track if already on disk, else any
        cached FreePD track, else None. Never touches the network — safe to
        call on the render hot path.
        """
        preferred = CACHE_DIR / _track_filename(TRACKS[_episode_index(episode_id)])
        if preferred.exists() and preferred.stat().st_size > MIN_AUDIO_BYTES:
            return preferred
        if CACHE_DIR.exists():
            for mp3 in sorted(CACHE_DIR.glob("*.mp3")):
                if mp3.stat().st_size > MIN_AUDIO_BYTES:
                    return mp3
        return None

    def select_track(self, episode_id: str) -> Path | None:
        """
        This episode's deterministic track (hash(episode_id) % len(TRACKS)),
        downloading it on first use. Returns cached path or None on failure.
        """
        url = TRACKS[_episode_index(episode_id)]
        dest = CACHE_DIR / _track_filename(url)
        if dest.exists() and dest.stat().st_size > MIN_AUDIO_BYTES:
            print(f"{LOG_TAG} cache hit: {dest.name}", flush=True)
            return dest
        return self._download(url, dest)

    def download_in_background(self, episode_id: str) -> threading.Thread:
        """
        Kick off this episode's track download on a daemon thread so the
        current render can proceed with the static theme; the NEXT render
        finds it cached. Returns the (already started) thread.
        """
        thread = threading.Thread(target=self.select_track, args=(episode_id,),
                                  name="freepd-download", daemon=True)
        thread.start()
        print(f"{LOG_TAG} background download started for {episode_id}", flush=True)
        return thread

    def prefetch_all(self) -> int:
        """Download every track in the list. Returns how many are now cached."""
        cached = 0
        for url in TRACKS:
            dest = CACHE_DIR / _track_filename(url)
            if (dest.exists() and dest.stat().st_size > MIN_AUDIO_BYTES) \
                    or self._download(url, dest):
                cached += 1
        return cached
