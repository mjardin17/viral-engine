"""
providers/ai_horde.py

AI Horde (stablehorde.net) — crowdsourced Stable Diffusion image generation.
COMPLETELY FREE, NO SIGNUP: the anonymous API key "0000000000" always works.

The trade-off is queue time — anonymous requests sit at the back of the
volunteer-GPU queue, so generation can take up to ~2 minutes. That makes
this a great LAST free fallback (after Pollinations) and a terrible primary.

Flow (async job):
  1. POST /api/v2/generate/async   → {"id": ...}
  2. GET  /api/v2/generate/check/{id}  poll until done=true
  3. GET  /api/v2/generate/status/{id} → generations[0].img (URL when r2=true,
                                          else base64)

Optional .env var: STABLE_HORDE_ANON_KEY (defaults to the anonymous key).
Registering a free account at stablehorde.net earns kudos → faster queue,
but is never required.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .base import ProviderBase

API_BASE = "https://stablehorde.net/api/v2"
ANON_KEY = "0000000000"
POLL_INTERVAL_SEC = 6.0
POLL_TIMEOUT_SEC = 120.0
MIN_IMAGE_BYTES = 10_000
LOG_TAG = "[ai_horde]"


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


class AIHordeProvider(ProviderBase):
    """AI Horde crowdsourced Stable Diffusion — always-free image fallback."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("STABLE_HORDE_ANON_KEY", "").strip() or ANON_KEY

    def is_connected(self) -> bool:
        """Always True — the anonymous key works without signup."""
        return True

    # ── HTTP helpers ───────────────────────────────────────────────────────
    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        """One JSON request to the Horde API; returns {"error": ...} on failure."""
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
            "Client-Agent": "EmpireOS:1.0:justifiedmagnificent@gmail.com",
        }
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(f"{API_BASE}{path}", data=data,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "body": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e), "body": ""}

    @staticmethod
    def _fetch_image_bytes(img_field: str) -> bytes | None:
        """generations[0].img is a URL (r2=true) or raw base64 — handle both."""
        if img_field.startswith("http"):
            try:
                req = urllib.request.Request(img_field, headers={"User-Agent": "EmpireOS/1.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return resp.read()
            except Exception as e:
                print(f"{LOG_TAG} R2 download failed: {e}", flush=True)
                return None
        try:
            return base64.b64decode(img_field)
        except Exception as e:
            print(f"{LOG_TAG} base64 decode failed: {e}", flush=True)
            return None

    # ── Main sync entry point (what the waterfall calls) ───────────────────
    def generate_image_file(self, prompt: str, dest: Path,
                            aspect_ratio: str = "16:9") -> bool:
        """
        Generate one image and save it to `dest`. Blocks up to POLL_TIMEOUT_SEC
        while the crowdsourced queue processes the job. Returns True on success.
        """
        # Horde requires dimensions in multiples of 64; keep small = fast queue.
        width, height = (768, 448) if aspect_ratio == "16:9" else (512, 512)
        submit = self._request("POST", "/generate/async", {
            "prompt": prompt[:900],
            "params": {"steps": 20, "width": width, "height": height, "n": 1},
            "models": ["stable_diffusion"],
            "r2": True,
        })
        job_id = submit.get("id")
        if not job_id:
            print(f"{LOG_TAG} submit failed: {submit.get('error', '')} "
                  f"| {str(submit.get('body', ''))[:300]}", flush=True)
            return False

        deadline = time.monotonic() + POLL_TIMEOUT_SEC
        while time.monotonic() < deadline:
            check = self._request("GET", f"/generate/check/{job_id}")
            if check.get("faulted"):
                print(f"{LOG_TAG} job {job_id} faulted", flush=True)
                return False
            if check.get("done"):
                break
            time.sleep(POLL_INTERVAL_SEC)
        else:
            print(f"{LOG_TAG} job {job_id} timed out after {POLL_TIMEOUT_SEC:.0f}s "
                  f"(queue position {check.get('queue_position', '?')})", flush=True)
            return False

        status = self._request("GET", f"/generate/status/{job_id}")
        generations = status.get("generations") or []
        if not generations:
            print(f"{LOG_TAG} job {job_id} done but returned no generations "
                  f"| {str(status.get('error', ''))[:200]}", flush=True)
            return False
        img_field = generations[0].get("img") or generations[0].get("url") or ""
        data = self._fetch_image_bytes(img_field) if img_field else None
        if not data or len(data) < MIN_IMAGE_BYTES:
            print(f"{LOG_TAG} image too small/empty "
                  f"({len(data) if data else 0} bytes)", flush=True)
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
        import tempfile
        dest = Path(tempfile.gettempdir()) / f"ai_horde_{abs(hash(prompt)) % 10**8}.png"
        ok = self.generate_image_file(prompt, dest, aspect_ratio)
        return {
            "status": "completed" if ok else "error",
            "job_id": None,
            "image_path": str(dest) if ok else None,
            "provider": "ai_horde",
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
        """Poll a Horde job directly (rarely needed — generate_image_file blocks)."""
        check = self._request("GET", f"/generate/check/{job_id}")
        done = bool(check.get("done"))
        return {"job_id": job_id,
                "status": "completed" if done else "processing",
                "output_url": None, "provider": "ai_horde"}
