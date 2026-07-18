"""
pollinations_adapter.py — IMAGE_GENERATION via Pollinations (free, keyless).

Delegates to the existing providers/waterfall.py _pollinations_image helper.
Payload: {"prompt": str, "dest": path}
"""

from __future__ import annotations

import sys
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class PollinationsAdapter(AdapterBase):
    """Pollinations AI image gen — always free, rate-limited ~1 req/s."""

    name = "pollinations"
    capability_score = 0.70
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        return True  # keyless public endpoint

    def execute(self, payload: dict) -> AdapterResult:
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        dest = Path(payload.get("dest") or "pollinations_image.jpg")
        try:
            from providers.waterfall import _pollinations_image
            out, ms = self._timed(_pollinations_image, prompt, dest)
            if out is not None and Path(out).exists():
                return AdapterResult(success=True, output=str(out), latency_ms=ms)
            return AdapterResult(success=False, latency_ms=ms,
                                 error="pollinations returned no image")
        except Exception as e:
            return AdapterResult(success=False, error=f"pollinations: {e}")
