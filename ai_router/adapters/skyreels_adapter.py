"""
skyreels_adapter.py — VIDEO_GENERATION via HF Space fffiloni/SkyReels-V2.

Uses HF_TOKEN + gradio_client.
Payload: {"prompt": str, "dest": mp4 path}
"""

from __future__ import annotations

from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult, env

SPACE = "fffiloni/SkyReels-V2"


class SkyReelsAdapter(AdapterBase):
    """SkyReels-V2 text-to-video via gradio Space (free HF credits)."""

    name = "skyreels"
    capability_score = 0.85
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        if not env("HF_TOKEN"):
            return False
        try:
            import gradio_client  # noqa: F401
            return True
        except ImportError:
            return False

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False,
                                 error="HF_TOKEN not set or gradio_client not installed")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        dest = Path(payload.get("dest") or "skyreels_out.mp4")
        try:
            from gradio_client import Client

            def _run():
                client = Client(SPACE, hf_token=env("HF_TOKEN"))
                return client.predict(prompt, api_name="/predict")

            result, ms = self._timed(_run)
            # Space returns a filepath (or dict with 'video') depending on version
            if isinstance(result, dict):
                result = result.get("video") or result.get("path") or ""
            if isinstance(result, (list, tuple)) and result:
                result = result[0]
            out = Path(str(result))
            if out.exists() and out.stat().st_size > 10_000:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(out.read_bytes())
                return AdapterResult(success=True, output=str(dest), latency_ms=ms)
            return AdapterResult(success=False, latency_ms=ms,
                                 error=f"SkyReels returned no usable video: {result!r:.120}")
        except Exception as e:
            return AdapterResult(success=False, error=f"skyreels: {e}")
