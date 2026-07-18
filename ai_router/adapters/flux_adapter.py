"""
flux_adapter.py — IMAGE_GENERATION via FAL FLUX.

Uses FAL_KEY (repo .env). Default model fal-ai/flux/schnell (fast/cheap);
payload {"quality": "pro"} switches to fal-ai/flux-pro.

POST https://queue.fal.run/<model>  {"prompt": ..., "image_size": "landscape_16_9"}
then polls the queue status URL until the image URL is ready.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult, env

MODEL_SCHNELL = "fal-ai/flux/schnell"
MODEL_PRO = "fal-ai/flux-pro"
POLL_SEC = 2.0
TIMEOUT_SEC = 180.0


class FluxAdapter(AdapterBase):
    """FLUX image generation on fal.ai queue API."""

    name = "flux"
    capability_score = 0.92
    default_cost_usd = 0.003  # schnell megapixel pricing ballpark

    def is_connected(self) -> bool:
        return bool(env("FAL_KEY"))

    def get_cost_estimate(self, payload: dict) -> float:
        return 0.05 if payload.get("quality") == "pro" else self.default_cost_usd

    def _request(self, url: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            url, data=data,
            headers={"Authorization": f"Key {env('FAL_KEY')}",
                     "Content-Type": "application/json"},
            method="POST" if body is not None else "GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="FAL_KEY not set")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        model = MODEL_PRO if payload.get("quality") == "pro" else MODEL_SCHNELL
        dest = Path(payload.get("dest") or "flux_image.jpg")
        start = time.monotonic()
        try:
            job = self._request(f"https://queue.fal.run/{model}", {
                "prompt": prompt,
                "image_size": str(payload.get("image_size", "landscape_16_9")),
            })
            status_url = job.get("status_url", "")
            response_url = job.get("response_url", "")
            if not status_url:
                return AdapterResult(success=False,
                                     error=f"fal submit failed: {str(job)[:200]}")
            deadline = time.monotonic() + TIMEOUT_SEC
            while time.monotonic() < deadline:
                status = self._request(status_url)
                state = str(status.get("status", "")).upper()
                if state == "COMPLETED":
                    break
                if state in ("FAILED", "CANCELLED"):
                    return AdapterResult(success=False, error=f"fal job {state}")
                time.sleep(POLL_SEC)
            else:
                return AdapterResult(success=False, error="fal job timed out")
            result = self._request(response_url)
            images = result.get("images") or []
            url = images[0].get("url", "") if images else ""
            if not url:
                return AdapterResult(success=False, error="fal returned no image URL")
            req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) < 10_000:
                return AdapterResult(success=False, error="fal image too small")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            ms = int((time.monotonic() - start) * 1000)
            return AdapterResult(success=True, output=str(dest), latency_ms=ms,
                                 cost_usd=self.get_cost_estimate(payload))
        except Exception as e:
            return AdapterResult(success=False, error=f"flux: {e}")
