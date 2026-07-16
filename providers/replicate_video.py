"""
providers/replicate_video.py

Replicate open-source video model provider for Empire OS.

Auth (checked in this order):
  1. REPLICATE_API_TOKEN in .env — direct Replicate API
     (new accounts get small trial credits; then pay-per-run)
  2. HF_TOKEN in .env — Hugging Face Inference Providers router, which can
     proxy Replicate/fal text-to-video models against HF's free monthly
     inference credits. HF_TOKEN is already set in this repo.

Direct Replicate flow (official model-scoped endpoint):
  POST https://api.replicate.com/v1/models/{owner}/{model}/predictions
  GET  https://api.replicate.com/v1/predictions/{id}

Default model: lightricks/ltx-video (fast, cheap open-source T2V).
Override with REPLICATE_VIDEO_MODEL in .env.

HF router flow:
  POST https://router.huggingface.co/v1/... — the text-to-video task is
  synchronous; we run it inline and return a pseudo job_id pointing at the
  already-downloaded temp file.
"""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .base import ProviderBase

REPLICATE_API_BASE = "https://api.replicate.com/v1"
DEFAULT_MODEL = "lightricks/ltx-video"
HF_T2V_URL = "https://router.huggingface.co/hf-inference/models/Lightricks/LTX-Video"

_LOCAL_PREFIX = "local:"  # pseudo job_id for synchronous HF results


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


class ReplicateVideoProvider(ProviderBase):
    """Replicate (or HF-router) open-source text-to-video provider."""

    def __init__(self) -> None:
        _load_env()
        self.replicate_token: str = os.environ.get("REPLICATE_API_TOKEN", "")
        self.hf_token: str = os.environ.get("HF_TOKEN", "")
        self.model: str = os.environ.get("REPLICATE_VIDEO_MODEL", DEFAULT_MODEL)

    def is_connected(self) -> bool:
        """True if either REPLICATE_API_TOKEN or HF_TOKEN is set."""
        return bool(self.replicate_token or self.hf_token)

    # ── HTTP helpers ───────────────────────────────────────────────────────
    def _replicate_request(self, url: str, payload: dict | None = None,
                           method: str = "GET") -> dict:
        """Call the Replicate REST API. Returns parsed JSON or {'error': ...}."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.replicate_token}",
        }
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    def _hf_generate_sync(self, prompt: str) -> dict:
        """Synchronous text-to-video via the HF Inference router (free credits)."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.hf_token}",
        }
        body = json.dumps({"inputs": prompt}).encode("utf-8")
        req = urllib.request.Request(HF_T2V_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = resp.read()
            if len(data) < 10_000:
                return {"error": f"HF returned too little data ({len(data)} bytes)"}
            tmp = Path(tempfile.gettempdir()) / f"hf_t2v_{abs(hash(prompt)) % 10**8}.mp4"
            tmp.write_bytes(data)
            return {"local_path": str(tmp)}
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    # ── ProviderBase interface ─────────────────────────────────────────────
    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """Submit a text-to-video job (Replicate async, or HF sync fallback)."""
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        if self.replicate_token:
            url = f"{REPLICATE_API_BASE}/models/{self.model}/predictions"
            payload = {"input": {"prompt": prompt, "aspect_ratio": aspect_ratio}}
            result = self._replicate_request(url, payload, method="POST")
            return {
                "status": "submitted" if result.get("id") else "error",
                "job_id": result.get("id"),
                "provider": "replicate",
                "model": self.model,
                "raw": result,
            }
        # HF router path — synchronous; wrap result in a pseudo job id
        result = self._hf_generate_sync(prompt)
        if "local_path" in result:
            return {
                "status": "submitted",
                "job_id": f"{_LOCAL_PREFIX}{result['local_path']}",
                "provider": "replicate_hf",
                "raw": result,
            }
        return {"status": "error", "job_id": None, "provider": "replicate_hf", "raw": result}

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Not wired — Gemini/Pollinations handle images in this pipeline."""
        return {"status": "not_supported", "message": "Use gemini_image/Pollinations for images."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported — Kokoro handles all narration."""
        return {"status": "not_supported", "message": "Kokoro is the pipeline voice engine."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Music not wired via Replicate."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "SFX not wired via Replicate."}

    def get_job_status(self, job_id: str) -> dict:
        """Poll a prediction; local: pseudo-jobs are already complete."""
        if job_id.startswith(_LOCAL_PREFIX):
            local = job_id[len(_LOCAL_PREFIX):]
            return {
                "job_id": job_id,
                "status": "completed" if Path(local).exists() else "failed",
                "output_url": f"file:///{local}",
                "local_path": local,
                "provider": "replicate_hf",
            }
        if not self.replicate_token:
            return self.not_connected_response("get_job_status")
        result = self._replicate_request(f"{REPLICATE_API_BASE}/predictions/{job_id}")
        state = str(result.get("status", "unknown")).lower()
        status = {"succeeded": "completed", "failed": "failed",
                  "canceled": "failed"}.get(state, "running")
        output = result.get("output")
        if isinstance(output, list):
            output = output[0] if output else None
        return {
            "job_id": job_id,
            "status": status if "error" not in result else "error",
            "output_url": output if status == "completed" else None,
            "provider": "replicate",
            "raw": result,
        }

    def download_clip(self, output_url: str, dest_path: str | Path) -> bool:
        """Download a clip; handles file:/// pseudo-URLs from the HF sync path."""
        if output_url.startswith("file:///"):
            src = Path(output_url[len("file:///"):])
            try:
                if src.exists() and src.stat().st_size > 10_000:
                    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(dest_path).write_bytes(src.read_bytes())
                    return True
            except Exception:
                pass
            return False
        return super().download_clip(output_url, dest_path)
