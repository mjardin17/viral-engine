"""
flux_kontext_adapter.py — IMAGE_EDITING with character consistency.

The "puzzle piece" compositing system for LO/IL characters: give it a
reference image URL + an edit prompt, get back a consistent-character edit.

Uses FAL_KEY. Model: fal-ai/flux-pro/kontext
Payload: {"prompt": str, "reference_image_url": str, "dest": path}
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult, env

MODEL = "fal-ai/flux-pro/kontext"
POLL_SEC = 2.0
TIMEOUT_SEC = 240.0


class FluxKontextAdapter(AdapterBase):
    """FLUX Kontext — reference-guided image editing (character consistency)."""

    name = "flux_kontext"
    capability_score = 0.93
    default_cost_usd = 0.04

    def is_connected(self) -> bool:
        return bool(env("FAL_KEY"))

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
        ref_url = str(payload.get("reference_image_url", "")).strip()
        if not prompt or not ref_url:
            return AdapterResult(
                success=False,
                error="flux_kontext needs 'prompt' AND 'reference_image_url'")
        dest = Path(payload.get("dest") or "flux_kontext_edit.jpg")
        start = time.monotonic()
        try:
            job = self._request(f"https://queue.fal.run/{MODEL}", {
                "prompt": prompt, "image_url": ref_url,
            })
            status_url = job.get("status_url", "")
            response_url = job.get("response_url", "")
            if not status_url:
                return AdapterResult(success=False,
                                     error=f"kontext submit failed: {str(job)[:200]}")
            deadline = time.monotonic() + TIMEOUT_SEC
            while time.monotonic() < deadline:
                status = self._request(status_url)
                state = str(status.get("status", "")).upper()
                if state == "COMPLETED":
                    break
                if state in ("FAILED", "CANCELLED"):
                    return AdapterResult(success=False, error=f"kontext job {state}")
                time.sleep(POLL_SEC)
            else:
                return AdapterResult(success=False, error="kontext job timed out")
            result = self._request(response_url)
            images = result.get("images") or []
            url = images[0].get("url", "") if images else ""
            if not url:
                return AdapterResult(success=False, error="kontext returned no image")
            req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) < 10_000:
                return AdapterResult(success=False, error="kontext image too small")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            ms = int((time.monotonic() - start) * 1000)
            return AdapterResult(success=True, output=str(dest), latency_ms=ms,
                                 cost_usd=self.default_cost_usd)
        except Exception as e:
            return AdapterResult(success=False, error=f"flux_kontext: {e}")
