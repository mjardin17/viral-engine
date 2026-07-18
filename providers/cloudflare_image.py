"""
providers/cloudflare_image.py

Cloudflare Workers AI — FLUX.1-schnell image generation.
FREE TIER: 10,000 neurons/day (hundreds of images) with a free Cloudflare
account. Fast (~2-5s per image) — the best free image slot ABOVE Pollinations.

Setup (30 seconds — see FREE_API_SETUP.md):
  1. Free account at https://dash.cloudflare.com
  2. Account ID: dashboard right sidebar → CF_ACCOUNT_ID in .env
  3. API token (Workers AI template): dash.cloudflare.com/profile/api-tokens
     → CF_API_TOKEN in .env

Endpoint:
  POST https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell
  Auth: Bearer token.
  Response: binary image bytes OR JSON {"result": {"image": "<base64>"}} —
  both shapes are handled (Cloudflare has shipped both over time).
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .base import ProviderBase

MODEL = "@cf/black-forest-labs/flux-1-schnell"
MIN_IMAGE_BYTES = 10_000
LOG_TAG = "[cloudflare_image]"


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


class CloudflareImageProvider(ProviderBase):
    """Cloudflare Workers AI FLUX-schnell — free 10k/day image generator."""

    def __init__(self) -> None:
        _load_env()
        self.account_id: str = os.environ.get("CF_ACCOUNT_ID", "").strip()
        self.api_token: str = os.environ.get("CF_API_TOKEN", "").strip()

    def is_connected(self) -> bool:
        """True when both CF_ACCOUNT_ID and CF_API_TOKEN are set in .env."""
        return bool(self.account_id and self.api_token)

    def generate_image_file(self, prompt: str, dest: Path,
                            aspect_ratio: str = "16:9") -> bool:
        """
        Generate one FLUX-schnell image and save it to `dest` (jpg/png bytes).
        Synchronous — returns True on success. Never raises.
        """
        if not self.is_connected():
            print(f"{LOG_TAG} SKIPPED — CF_ACCOUNT_ID/CF_API_TOKEN not set in .env",
                  flush=True)
            return False
        url = (f"https://api.cloudflare.com/client/v4/accounts/"
               f"{self.account_id}/ai/run/{MODEL}")
        payload = json.dumps({"prompt": prompt[:2000], "num_steps": 4}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            print(f"{LOG_TAG} HTTP {e.code}: {body}", flush=True)
            return False
        except Exception as e:
            print(f"{LOG_TAG} request failed: {e}", flush=True)
            return False

        data: bytes | None = None
        if "application/json" in content_type:
            try:
                b64 = (json.loads(raw.decode("utf-8")).get("result") or {}).get("image")
                data = base64.b64decode(b64) if b64 else None
            except Exception as e:
                print(f"{LOG_TAG} JSON/base64 parse failed: {e}", flush=True)
        else:
            data = raw  # binary image response (image/jpeg or image/png)

        if not data or len(data) < MIN_IMAGE_BYTES:
            print(f"{LOG_TAG} image too small/empty "
                  f"({len(data) if data else 0} bytes, ct={content_type})", flush=True)
            return False
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return True
        except OSError as e:
            print(f"{LOG_TAG} could not write {dest}: {e}", flush=True)
            return False

    # ── ProviderBase interface ─────────────────────────────────────────────
    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Synchronous image generation. Saves to a temp path and returns it."""
        if not self.is_connected():
            return self.not_connected_response("generate_image")
        import tempfile
        dest = Path(tempfile.gettempdir()) / f"cf_img_{abs(hash(prompt)) % 10**8}.jpg"
        ok = self.generate_image_file(prompt, dest, aspect_ratio)
        return {
            "status": "completed" if ok else "error",
            "job_id": None,
            "image_path": str(dest) if ok else None,
            "provider": "cloudflare_image",
        }

    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """Not supported — image-only provider."""
        return {"status": "not_supported", "message": "Image-only provider (Ken Burns source)."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Kokoro handles narration."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "No music support."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "No SFX support."}

    def get_job_status(self, job_id: str) -> dict:
        """Synchronous provider — there are never pending jobs."""
        return {"job_id": job_id, "status": "completed", "output_url": None,
                "provider": "cloudflare_image"}
