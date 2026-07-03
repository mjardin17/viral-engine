"""
providers/runway.py

Runway ML provider adapter for Empire Decoded.
API key: set RUNWAY_API_KEY in .env or environment.
Runway Gen-3 Alpha Turbo for video generation.
"""

import json
import os
import urllib.request
import urllib.error
from .base import ProviderBase


RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"


def _load_env():
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


class RunwayProvider(ProviderBase):

    def __init__(self):
        _load_env()
        self.api_key = os.environ.get("RUNWAY_API_KEY", "")

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Version": "2024-11-06",
        }

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{RUNWAY_API_BASE}{endpoint}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    def _get(self, endpoint: str) -> dict:
        url = f"{RUNWAY_API_BASE}{endpoint}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def is_connected(self) -> bool:
        return bool(self.api_key)

    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        # Runway duration must be 5 or 10 seconds
        duration = 10 if duration_sec >= 8 else 5
        payload = {
            "promptText": prompt,
            "model": "gen3a_turbo",
            "duration": duration,
            "ratio": aspect_ratio,
        }
        if reference_image_path:
            payload["promptImage"] = reference_image_path
        result = self._post("/image_to_video", payload)
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("id"),
            "provider": "runway",
            "model": "gen3a_turbo",
            "raw": result,
        }

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        return {"status": "not_supported", "message": "Runway does not support image generation. Use Higgsfield."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        return {"status": "not_supported", "message": "Runway does not support audio. Use Higgsfield for narration."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        return {"status": "not_supported", "message": "Runway does not support music. Use Higgsfield."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        return {"status": "not_supported", "message": "Runway does not support SFX. Use Higgsfield."}

    def get_job_status(self, job_id: str) -> dict:
        if not self.is_connected():
            return self.not_connected_response("get_job_status")
        result = self._get(f"/tasks/{job_id}")
        return {
            "job_id": job_id,
            "status": result.get("status", "unknown"),
            "output_url": (result.get("output") or [""])[0],
            "provider": "runway",
            "raw": result,
        }
