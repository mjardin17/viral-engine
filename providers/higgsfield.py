"""
providers/higgsfield.py

Higgsfield provider adapter for Empire Decoded.

API key: set HIGGSFIELD_API_KEY in .env or environment.

Models used:
  - nano_banana_2       → character reference images
  - grok_video          → scene video clips
  - inworld_text_to_speech → narration (Hades voice)
  - sonilo_music        → background music score
  - mirelo_text_to_audio → sound effects

Higgsfield REST API base: https://api.higgsfield.ai
"""

import json
import os
import urllib.request
import urllib.error
from .base import ProviderBase


HIGGSFIELD_API_BASE = "https://api.higgsfield.ai/v1"

# Model IDs
MODEL_IMAGE = "nano_banana_2"
MODEL_VIDEO = "grok_video"
MODEL_TTS   = "inworld_text_to_speech"
MODEL_MUSIC = "sonilo_music"
MODEL_SFX   = "mirelo_text_to_audio"

# Voice for narration
NARRATION_VOICE = "Hades"


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
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


class HiggssfieldProvider(ProviderBase):

    def __init__(self):
        _load_env()
        self.api_key = os.environ.get("HIGGSFIELD_API_KEY", "")

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{HIGGSFIELD_API_BASE}{endpoint}"
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
        url = f"{HIGGSFIELD_API_BASE}{endpoint}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def is_connected(self) -> bool:
        return bool(self.api_key)

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        if not self.is_connected():
            return self.not_connected_response("generate_image")
        payload = {
            "model": MODEL_IMAGE,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }
        result = self._post("/generate/image", payload)
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("job_id") or result.get("id"),
            "provider": "higgsfield",
            "model": MODEL_IMAGE,
            "raw": result,
        }

    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        payload = {
            "model": MODEL_VIDEO,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration_sec,
        }
        if reference_image_path:
            payload["reference_image"] = reference_image_path
        result = self._post("/generate/video", payload)
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("job_id") or result.get("id"),
            "provider": "higgsfield",
            "model": MODEL_VIDEO,
            "raw": result,
        }

    def generate_audio(self, prompt: str, voice: str = NARRATION_VOICE,
                       duration_sec: int = 10) -> dict:
        if not self.is_connected():
            return self.not_connected_response("generate_audio")
        payload = {
            "model": MODEL_TTS,
            "text": prompt,
            "voice": voice,
        }
        result = self._post("/generate/audio", payload)
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("job_id") or result.get("id"),
            "provider": "higgsfield",
            "model": MODEL_TTS,
            "voice": voice,
            "raw": result,
        }

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        if not self.is_connected():
            return self.not_connected_response("generate_music")
        payload = {
            "model": MODEL_MUSIC,
            "prompt": prompt,
            "duration": duration_sec,
        }
        result = self._post("/generate/audio", payload)
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("job_id") or result.get("id"),
            "provider": "higgsfield",
            "model": MODEL_MUSIC,
            "raw": result,
        }

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        if not self.is_connected():
            return self.not_connected_response("generate_sfx")
        payload = {
            "model": MODEL_SFX,
            "prompt": prompt,
            "duration": duration_sec,
        }
        result = self._post("/generate/audio", payload)
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("job_id") or result.get("id"),
            "provider": "higgsfield",
            "model": MODEL_SFX,
            "raw": result,
        }

    def get_job_status(self, job_id: str) -> dict:
        if not self.is_connected():
            return self.not_connected_response("get_job_status")
        result = self._get(f"/jobs/{job_id}")
        return {
            "job_id": job_id,
            "status": result.get("status", "unknown"),
            "output_url": result.get("output_url") or result.get("url"),
            "provider": "higgsfield",
            "raw": result,
        }
