"""
higgsfield_adapter.py — PAID last-resort video (wraps existing provider).

Delegates to providers/higgsfield.py + providers/waterfall.py lifecycle.
Same 10-second credit-guard warning as providers/waterfall.py (Higgsfield
credits are real money — Josh gets a Ctrl+C window before any paid call).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult, env

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PAID_WARNING_SEC = 10


class HiggsfieldAdapter(AdapterBase):
    """Higgsfield — highest quality stylized cartoon video. PAID."""

    name = "higgsfield"
    capability_score = 0.95
    default_cost_usd = 0.50

    def is_connected(self) -> bool:
        return bool(env("HIGGSFIELD_API_KEY"))

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="HIGGSFIELD_API_KEY not set")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        dest = Path(payload.get("dest") or "higgsfield_out.mp4")
        duration = int(payload.get("duration_sec", 5))
        aspect = str(payload.get("aspect_ratio", "16:9"))
        try:
            # Credit guard — mirrors providers/waterfall.py behavior exactly.
            print(f"[higgsfield_adapter] ⚠️ WARNING: about to use Higgsfield (PAID). "
                  f"Press Ctrl+C within {PAID_WARNING_SEC} seconds to cancel.",
                  file=sys.stderr, flush=True)
            time.sleep(PAID_WARNING_SEC)
            print("[higgsfield_adapter] no cancel — proceeding with PAID Higgsfield",
                  file=sys.stderr, flush=True)

            from providers.higgsfield import HiggssfieldProvider
            from providers.waterfall import _run_video_provider
            provider = HiggssfieldProvider()
            clip, ms = self._timed(
                _run_video_provider, provider, "higgsfield", prompt, duration,
                aspect, dest)
            if clip is not None:
                return AdapterResult(success=True, output=str(clip), latency_ms=ms,
                                     cost_usd=self.default_cost_usd)
            return AdapterResult(success=False, latency_ms=ms,
                                 error="higgsfield job produced no clip")
        except KeyboardInterrupt:
            return AdapterResult(success=False, error="cancelled by Josh (credit guard)")
        except Exception as e:
            return AdapterResult(success=False, error=f"higgsfield: {e}")
