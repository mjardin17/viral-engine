"""
providers/luma.py

Luma AI Dream Machine provider adapter for Empire OS.

API key: set LUMA_API_KEY in .env or environment.
Get a key at https://lumalabs.ai/api (Dream Machine API).

NOTE (research 2026-07): the Dream Machine *API* is pay-as-you-go
(~$0.32/generation) — Luma's free tier (~80 credits/day) applies to the
web app only, NOT the API. This provider stays dark unless Josh adds a
funded/promo key. It sits high in the waterfall so it lights up
automatically the moment a key appears.

Endpoint docs: https://docs.lumalabs.ai/docs/api
  POST https://api.lumalabs.ai/dream-machine/v1/generations
  GET  https://api.lumalabs.ai/dream-machine/v1/generations/{id}
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ProviderBase

LUMA_API_BASE = "https://api.lumalabs.ai/dream-machine/v1"
LUMA_MODEL = "ray-2"
# Ray-2 accepts fixed duration strings
_VALID_DURATIONS = (5, 9)


def _load_env() -> None:
    """Populate os.environ from the repo-root .env (never overrides existing vars)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


class LumaProvider(ProviderBase):
    """Luma Dream Machine (Ray-2) text-to-video provider."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("LUMA_API_KEY", "")

    def is_connected(self) -> bool:
        """True if LUMA_API_KEY is set."""
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _request(self, endpoint: str, payload: dict | None = None, method: str = "GET") -> dict:
        """Low-level HTTP helper. Returns parsed JSON or {'error': ...}."""
        url = f"{LUMA_API_BASE}{endpoint}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """Submit a Dream Machine text-to-video job. Returns job info dict."""
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        duration = min(_VALID_DURATIONS, key=lambda d: abs(d - duration_sec))
        payload: dict = {
            "prompt": prompt,
            "model": LUMA_MODEL,
            "aspect_ratio": aspect_ratio,
            "duration": f"{duration}s",
            "resolution": "720p",
        }
        if reference_image_path:
            payload["keyframes"] = {"frame0": {"type": "image", "url": reference_image_path}}
        result = self._request("/generations", payload, method="POST")
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("id"),
            "provider": "luma_ai",
            "raw": result,
        }

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Luma image generation not wired — video-only in this pipeline."""
        return {"status": "not_supported", "message": "Luma used for video only in Empire OS."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported — Kokoro handles all narration."""
        return {"status": "not_supported", "message": "Luma does not support audio."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Luma does not support music."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Luma does not support SFX."}

    def get_job_status(self, job_id: str) -> dict:
        """Poll a generation. Maps Luma states → completed/running/failed."""
        if not self.is_connected():
            return self.not_connected_response("get_job_status")
        result = self._request(f"/generations/{job_id}")
        state = str(result.get("state", "unknown")).lower()
        status = {"completed": "completed", "failed": "failed"}.get(state, "running")
        output_url: str | None = None
        if status == "completed":
            output_url = (result.get("assets") or {}).get("video")
        return {
            "job_id": job_id,
            "status": status if "error" not in result else "error",
            "output_url": output_url,
            "provider": "luma_ai",
            "raw": result,
        }
