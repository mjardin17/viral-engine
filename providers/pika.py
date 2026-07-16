"""
providers/pika.py

Pika Labs provider adapter for Empire OS.

API key: set PIKA_API_KEY in .env or environment.
Keys are issued at pika.art → Settings → Developer → API Keys.

NOTE (research 2026-07): Pika API access requires a Pro or Enterprise
subscription (~$28/mo Pro; API billed ~$0.05/generated second). The free
tier (80 credits/mo, 480p) is web/Discord only — NO free API. This
provider is a best-effort adapter that stays dark until a paid key is
added; endpoint shapes are marked [Guessing] where Pika has not published
public REST docs — verify against the developer dashboard before relying
on it in production.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ProviderBase

# [Guessing] — Pika's public REST base; confirm in the Pro developer dashboard.
PIKA_API_BASE = "https://api.pika.art/v1"


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


class PikaProvider(ProviderBase):
    """Pika Labs text-to-video provider (paid API — dark until key added)."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("PIKA_API_KEY", "")

    def is_connected(self) -> bool:
        """True if PIKA_API_KEY is set."""
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _request(self, endpoint: str, payload: dict | None = None, method: str = "GET") -> dict:
        """Low-level HTTP helper. Returns parsed JSON or {'error': ...}."""
        url = f"{PIKA_API_BASE}{endpoint}"
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
        """Submit a Pika text-to-video job. Returns job info dict."""
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        payload: dict = {
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "duration": duration_sec,
        }
        if reference_image_path:
            payload["image"] = reference_image_path
        result = self._request("/videos", payload, method="POST")
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("id") or result.get("video_id") or result.get("job_id"),
            "provider": "pika",
            "raw": result,
        }

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Pika is video-only."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Pika does not support audio."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Pika does not support music."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Pika does not support SFX."}

    def get_job_status(self, job_id: str) -> dict:
        """Poll a Pika job until completed. Returns output_url when done."""
        if not self.is_connected():
            return self.not_connected_response("get_job_status")
        result = self._request(f"/videos/{job_id}")
        state = str(result.get("status", "unknown")).lower()
        status = {"finished": "completed", "completed": "completed",
                  "failed": "failed", "error": "failed"}.get(state, "running")
        output_url = result.get("url") or result.get("video_url") or (result.get("result") or {}).get("url")
        return {
            "job_id": job_id,
            "status": status if "error" not in result else "error",
            "output_url": output_url if status == "completed" else None,
            "provider": "pika",
            "raw": result,
        }
