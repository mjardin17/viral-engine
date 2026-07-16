"""
providers/minimax.py

MiniMax (Hailuo) provider adapter for Empire OS.

API key: set MINIMAX_API_KEY in .env or environment.
Keys: https://platform.minimax.io (International) — API keys under
Account → API Keys. New accounts get a small trial credit; ongoing use is
pay-as-you-go (1 video point ≈ one 768p/6s Hailuo-02 clip).

Flow (per MiniMax API docs, platform.minimax.io/docs):
  1. POST /v1/video_generation            → task_id
  2. GET  /v1/query/video_generation?task_id=  → status + file_id when Success
  3. GET  /v1/files/retrieve?file_id=          → download_url

get_job_status() folds steps 2-3 together so the waterfall only sees
{status, output_url}.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ProviderBase

MINIMAX_API_BASE = "https://api.minimax.io/v1"
MINIMAX_MODEL = "MiniMax-Hailuo-02"


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


class MinimaxProvider(ProviderBase):
    """MiniMax Hailuo text-to-video provider."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("MINIMAX_API_KEY", "")

    def is_connected(self) -> bool:
        """True if MINIMAX_API_KEY is set."""
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _request(self, endpoint: str, payload: dict | None = None, method: str = "GET") -> dict:
        """Low-level HTTP helper. Returns parsed JSON or {'error': ...}."""
        url = f"{MINIMAX_API_BASE}{endpoint}"
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
        """Submit a Hailuo text-to-video job (6s or 10s @768P). Returns job info."""
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        duration = 6 if duration_sec <= 8 else 10
        payload: dict = {
            "model": MINIMAX_MODEL,
            "prompt": prompt,
            "duration": duration,
            "resolution": "768P",
        }
        if reference_image_path:
            payload["first_frame_image"] = reference_image_path
        result = self._request("/video_generation", payload, method="POST")
        return {
            "status": "submitted" if "error" not in result and result.get("task_id") else "error",
            "job_id": result.get("task_id"),
            "provider": "minimax",
            "raw": result,
        }

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Not wired — Gemini/Pollinations handle images in this pipeline."""
        return {"status": "not_supported", "message": "MiniMax used for video only in Empire OS."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported — Kokoro handles all narration."""
        return {"status": "not_supported", "message": "MiniMax TTS not wired — Kokoro is primary."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "MiniMax music not wired."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "MiniMax SFX not wired."}

    def get_job_status(self, job_id: str) -> dict:
        """Poll task; on Success also resolves file_id → download_url."""
        if not self.is_connected():
            return self.not_connected_response("get_job_status")
        result = self._request(f"/query/video_generation?task_id={job_id}")
        state = str(result.get("status", "unknown")).lower()
        status = {"success": "completed", "fail": "failed"}.get(state, "running")
        output_url: str | None = None
        if status == "completed":
            file_id = result.get("file_id")
            if file_id:
                file_info = self._request(f"/files/retrieve?file_id={file_id}")
                output_url = (file_info.get("file") or {}).get("download_url")
            if not output_url:
                status = "failed"
        return {
            "job_id": job_id,
            "status": status if "error" not in result else "error",
            "output_url": output_url,
            "provider": "minimax",
            "raw": result,
        }
