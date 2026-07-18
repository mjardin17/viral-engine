"""
wan22_adapter.py — ANIMATION / VIDEO_GENERATION via Replicate Wan 2.2.

Uses REPLICATE_API_TOKEN (repo .env). Delegates job lifecycle to the
EXISTING providers/replicate_video.py + providers/waterfall.py machinery —
no duplicated polling code. Model slug default "wan-video/wan-2.2-t2v-fast"
(override with WAN22_REPLICATE_MODEL env var if the slug moves).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult, env

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# [Likely] Current Replicate slug for Wan 2.2 text-to-video (fast variant).
DEFAULT_MODEL = "wan-video/wan-2.2-t2v-fast"


class Wan22Adapter(AdapterBase):
    """Wan 2.2 on Replicate — animation-grade text-to-video."""

    name = "wan22"
    capability_score = 0.90
    default_cost_usd = 0.10

    def is_connected(self) -> bool:
        return bool(env("REPLICATE_API_TOKEN"))

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="REPLICATE_API_TOKEN not set")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        dest = Path(payload.get("dest") or "wan22_out.mp4")
        duration = int(payload.get("duration_sec", 5))
        aspect = str(payload.get("aspect_ratio", "16:9"))
        model = env("WAN22_REPLICATE_MODEL") or DEFAULT_MODEL
        try:
            from providers.replicate_video import ReplicateVideoProvider
            from providers.waterfall import _run_video_provider

            # Point the existing provider at the Wan 2.2 slug for this call
            os.environ.setdefault("REPLICATE_VIDEO_MODEL", model)
            provider = ReplicateVideoProvider()

            clip, ms = self._timed(
                _run_video_provider, provider, "wan22", prompt, duration, aspect, dest)
            if clip is not None:
                return AdapterResult(success=True, output=str(clip), latency_ms=ms,
                                     cost_usd=self.default_cost_usd)
            return AdapterResult(success=False, latency_ms=ms,
                                 error="wan22 replicate job produced no clip")
        except Exception as e:
            return AdapterResult(success=False, error=f"wan22: {e}")
