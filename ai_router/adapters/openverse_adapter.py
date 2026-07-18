"""
openverse_adapter.py — wraps existing providers/openverse.py (free, no key).

Serves MUSIC fallback ("openverse_audio") and CC image fetch.
Payload: {"prompt": str, "dest": path, "aspect_ratio": optional}
"""

from __future__ import annotations

import sys
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class OpenverseAdapter(AdapterBase):
    """Openverse CC media — delegates to OpenverseProvider."""

    name = "openverse_audio"
    capability_score = 0.75
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        try:
            from providers.openverse import OpenverseProvider
            return OpenverseProvider().is_connected()
        except Exception:
            return False

    def execute(self, payload: dict) -> AdapterResult:
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        dest = Path(payload.get("dest") or "openverse_asset.jpg")
        aspect = str(payload.get("aspect_ratio", "16:9"))
        try:
            from providers.openverse import OpenverseProvider
            provider = OpenverseProvider()
            out, ms = self._timed(provider.fetch_image, prompt, dest, aspect)
            if out is not None and Path(out).exists():
                return AdapterResult(success=True, output=str(out), latency_ms=ms)
            return AdapterResult(success=False, latency_ms=ms,
                                 error="openverse found nothing usable")
        except Exception as e:
            return AdapterResult(success=False, error=f"openverse: {e}")
