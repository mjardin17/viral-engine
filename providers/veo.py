"""
providers/veo.py

Google Veo provider adapter for Empire Decoded.
API key: set VEO_API_KEY in .env or environment.
Uses Google's Vertex AI / Veo video generation endpoint.
"""

import json
import os
import urllib.request
import urllib.error
from .base import ProviderBase


VEO_API_BASE = "https://us-central1-aiplatform.googleapis.com/v1"


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


class VeoProvider(ProviderBase):

    def __init__(self):
        _load_env()
        self.api_key = os.environ.get("VEO_API_KEY", "")
        self.project_id = os.environ.get("VEO_PROJECT_ID", "")

    def is_connected(self) -> bool:
        return bool(self.api_key and self.project_id)

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{VEO_API_BASE}{endpoint}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        endpoint = f"/projects/{self.project_id}/locations/us-central1/publishers/google/models/veo-2:generateVideo"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "aspectRatio": aspect_ratio,
                "durationSeconds": duration_sec,
                "sampleCount": 1,
            },
        }
        result = self._post(endpoint, payload)
        return {
            "status": "submitted" if "error" not in result else "error",
            "job_id": result.get("name"),
            "provider": "veo",
            "raw": result,
        }

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        return {"status": "not_supported", "message": "Veo is video-only. Use Higgsfield for character images."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        return {"status": "not_supported", "message": "Veo does not support audio. Use Higgsfield for narration."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        return {"status": "not_supported", "message": "Veo does not support music. Use Higgsfield."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        return {"status": "not_supported", "message": "Veo does not support SFX. Use Higgsfield."}

    def get_job_status(self, job_id: str) -> dict:
        if not self.is_connected():
            return self.not_connected_response("get_job_status")
        url = f"{VEO_API_BASE}/{job_id}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"job_id": job_id, "status": "error", "error": str(e)}
        done = result.get("done", False)
        output_url = None
        if done:
            output_url = result.get("response", {}).get("videos", [{}])[0].get("uri")
        return {
            "job_id": job_id,
            "status": "completed" if done else "running",
            "output_url": output_url,
            "provider": "veo",
            "raw": result,
        }
