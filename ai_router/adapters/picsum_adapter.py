"""
picsum_adapter.py — LAST RESORT placeholder image (existing providers/picsum.py).

capability 0.20: image is UNRELATED to the prompt — beats a black frame only.
Payload: {"prompt": str (ignored by picsum), "dest": path}
"""

from __future__ import annotations

import sys
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class PicsumAdapter(AdapterBase):
    """Lorem Picsum random placeholder — absolute last resort."""

    name = "picsum"
    capability_score = 0.20
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        try:
            from providers.picsum import PicsumProvider
            return PicsumProvider().is_connected()
        except Exception:
            return False

    def execute(self, payload: dict) -> AdapterResult:
        dest = Path(payload.get("dest") or "picsum_placeholder.jpg")
        prompt = str(payload.get("prompt", "placeholder"))
        aspect = str(payload.get("aspect_ratio", "16:9"))
        try:
            from providers.picsum import PicsumProvider
            out, ms = self._timed(PicsumProvider().fetch_image, prompt, dest, aspect)
            if out is not None and Path(out).exists():
                return AdapterResult(success=True, output=str(out), latency_ms=ms,
                                     meta={"warning": "placeholder — unrelated to prompt"})
            return AdapterResult(success=False, latency_ms=ms,
                                 error="picsum fetch failed")
        except Exception as e:
            return AdapterResult(success=False, error=f"picsum: {e}")
