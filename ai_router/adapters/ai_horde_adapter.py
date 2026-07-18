"""
ai_horde_adapter.py — IMAGE_GENERATION via existing providers/ai_horde.py.

Anonymous crowdsourced Stable Diffusion — always free, slow queue.
Payload: {"prompt": str, "dest": path, "aspect_ratio": optional}
"""

from __future__ import annotations

import sys
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class AIHordeAdapter(AdapterBase):
    """AI Horde image gen — free, anonymous, slow."""

    name = "ai_horde"
    capability_score = 0.60
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        return True  # anonymous key — always available

    def execute(self, payload: dict) -> AdapterResult:
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        dest = Path(payload.get("dest") or "ai_horde_image.png")
        aspect = str(payload.get("aspect_ratio", "16:9"))
        try:
            from providers.ai_horde import AIHordeProvider
            ok, ms = self._timed(
                AIHordeProvider().generate_image_file, prompt, dest, aspect)
            if ok and dest.exists() and dest.stat().st_size > 10_000:
                return AdapterResult(success=True, output=str(dest), latency_ms=ms)
            return AdapterResult(success=False, latency_ms=ms,
                                 error="ai_horde produced no image")
        except Exception as e:
            return AdapterResult(success=False, error=f"ai_horde: {e}")
