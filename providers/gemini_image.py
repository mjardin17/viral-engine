"""
providers/gemini_image.py

Gemini image-generation provider for Empire OS — the GUARANTEED free
fallback for LO/IL scene visuals.

API key: GEMINI_API_KEY (already in .env, already confirmed working).
Free tier (verified 2026-07): gemini-2.5-flash-image ("Nano Banana") —
~500 images/day at 1024px, no credit card. Imagen via API is paid-tier
rate-limited (2 IPM free), so Nano Banana is primary.

Synchronous: generateContent returns the image inline (base64) — no job
polling needed. generate_image_file() is the method the waterfall calls.

Endpoint:
  POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
  header: x-goog-api-key
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .base import ProviderBase

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Tried in order — first model that returns an image wins.
# Verified working July 2026: gemini-2.0-flash-preview-image-generation
MODEL_CANDIDATES: tuple[str, ...] = (
    "gemini-2.0-flash-preview-image-generation",
    "gemini-2.5-flash-image",
)
# Fallback if every generateContent model fails — Imagen predict API.
IMAGEN_FALLBACK_MODEL = "imagen-3.0-generate-002"
LOG_TAG = "[gemini_image]"


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


class GeminiImageProvider(ProviderBase):
    """Gemini (Nano Banana) free-tier image generator — Ken Burns source images."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("GEMINI_API_KEY", "")

    def is_connected(self) -> bool:
        """True if GEMINI_API_KEY is set."""
        return bool(self.api_key)

    def _post_json(self, url: str, payload: dict) -> dict:
        """POST JSON to a Gemini endpoint; on failure return {"error", "body"}."""
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e), "body": ""}

    def _generate_content(self, model: str, prompt: str) -> dict:
        """Call generateContent asking for an IMAGE response modality."""
        url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": f"Generate a historical image: {prompt}"}]}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
        }
        return self._post_json(url, payload)

    def _generate_imagen(self, prompt: str, aspect_ratio: str) -> bytes | None:
        """Last-resort fallback: Imagen predict API (paid-tier rate limited)."""
        url = f"{GEMINI_API_BASE}/models/{IMAGEN_FALLBACK_MODEL}:predict"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": aspect_ratio},
        }
        result = self._post_json(url, payload)
        if "error" in result:
            print(f"{LOG_TAG} {IMAGEN_FALLBACK_MODEL} FAILED: {result['error']} "
                  f"| response: {result.get('body', '')[:500]}", flush=True)
            return None
        for prediction in result.get("predictions", []):
            b64 = prediction.get("bytesBase64Encoded")
            if b64:
                try:
                    return base64.b64decode(b64)
                except Exception as e:
                    print(f"{LOG_TAG} Imagen base64 decode failed: {e}", flush=True)
        print(f"{LOG_TAG} {IMAGEN_FALLBACK_MODEL} returned no image data "
              f"(keys: {list(result.keys())})", flush=True)
        return None

    @staticmethod
    def _extract_image_bytes(result: dict) -> bytes | None:
        """Pull the first inline base64 image out of a generateContent response."""
        for candidate in result.get("candidates", []):
            for part in (candidate.get("content") or {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    try:
                        return base64.b64decode(inline["data"])
                    except Exception:
                        continue
        return None

    def generate_image_file(self, prompt: str, dest: Path,
                            aspect_ratio: str = "16:9") -> bool:
        """
        Generate an illustration for a scene and save it to `dest`.
        Tries each model candidate; returns True on the first success.
        Synchronous — this is what waterfall.py calls.
        """
        if not self.is_connected():
            print(f"{LOG_TAG} SKIPPED — GEMINI_API_KEY not set in .env", flush=True)
            return False
        styled = (f"{prompt}. Cinematic wide illustration, {aspect_ratio} aspect ratio, "
                  f"vibrant colors, high detail, no text, no watermark.")
        data: bytes | None = None
        for model in MODEL_CANDIDATES:
            result = self._generate_content(model, styled)
            if "error" in result:
                # Loud failure — silent fall-through hid a dead model name for weeks.
                print(f"{LOG_TAG} {model} FAILED: {result['error']} "
                      f"| response: {result.get('body', '')[:500]}", flush=True)
                continue
            data = self._extract_image_bytes(result)
            if data and len(data) > 10_000:
                break
            print(f"{LOG_TAG} {model} returned no usable image "
                  f"(got {len(data) if data else 0} bytes) — trying next", flush=True)
            data = None
        if data is None:
            print(f"{LOG_TAG} all generateContent models failed — "
                  f"trying Imagen fallback {IMAGEN_FALLBACK_MODEL}", flush=True)
            data = self._generate_imagen(styled, aspect_ratio)
        if data and len(data) > 10_000:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                return True
            except OSError as e:
                print(f"{LOG_TAG} could not write {dest}: {e}", flush=True)
                return False
        return False

    # ── ProviderBase interface ─────────────────────────────────────────────
    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Synchronous image generation. Saves to a temp path and returns it."""
        if not self.is_connected():
            return self.not_connected_response("generate_image")
        import tempfile
        dest = Path(tempfile.gettempdir()) / f"gemini_img_{abs(hash(prompt)) % 10**8}.png"
        ok = self.generate_image_file(prompt, dest, aspect_ratio)
        return {
            "status": "completed" if ok else "error",
            "job_id": None,
            "image_path": str(dest) if ok else None,
            "provider": "gemini_image",
        }

    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """Not supported — this provider makes stills for Ken Burns motion."""
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
                "provider": "gemini_image"}
