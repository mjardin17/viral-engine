"""
freepd_adapter.py — MUSIC via existing providers/freepd_music.py (free).

Payload: {"episode_id": str}  → output = local mp3 track path
"""

from __future__ import annotations

import sys

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class FreePDAdapter(AdapterBase):
    """FreePD public-domain music — delegates to FreePDMusicProvider."""

    name = "freepd"
    capability_score = 0.80
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        try:
            from providers.freepd_music import FreePDMusicProvider
            return FreePDMusicProvider().is_connected()
        except Exception:
            return False

    def execute(self, payload: dict) -> AdapterResult:
        episode_id = str(payload.get("episode_id") or payload.get("prompt") or "EP000")
        try:
            from providers.freepd_music import FreePDMusicProvider
            provider = FreePDMusicProvider()
            track, ms = self._timed(
                lambda: provider.get_cached_track(episode_id)
                or provider.select_track(episode_id))
            if track is not None and track.exists():
                return AdapterResult(success=True, output=str(track), latency_ms=ms)
            return AdapterResult(success=False, latency_ms=ms,
                                 error="FreePD returned no track")
        except Exception as e:
            return AdapterResult(success=False, error=f"freepd: {e}")
