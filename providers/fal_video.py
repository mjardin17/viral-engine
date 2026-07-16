"""
providers/fal_video.py

Direct fal.ai video generation — uses fal's own queue API with FAL_KEY.

Free-tier reality (researched 2026-07-16):
  * fal.ai gives ONE-TIME signup credits (~$10-20 with a business email) —
    there is NO permanent free tier. Credits are prepaid and drawn per run.
  * Cheap models stretch those credits far: LTX distilled clips cost cents;
    Wan 2.2 T2V is mid-priced; Kling 3 Pro is ~$0.22-0.28/second (avoid).
  * Signup: https://fal.ai → dashboard → Keys → paste into FAL_KEY in .env.

Why keep this provider when hf_video also routes to fal? Because it burns
fal signup credits instead of HF monthly credits — a separate free pool.
Waterfall order puts fal_video before hf_video for exactly that reason.

Queue protocol (https://docs.fal.ai/model-apis/queue):
  1. POST https://queue.fal.run/{model}   Authorization: Key {FAL_KEY}
     → {"request_id", "status_url", "response_url"} (absolute URLs)
  2. Poll status_url until status == "COMPLETED"
  3. GET response_url → {"video": {"url": ...}} → download MP4.

Env:
  FAL_KEY           (required — get from https://fal.ai/dashboard/keys)
  FAL_VIDEO_MODEL   optional override, default fal-ai/ltxv-13b-098-distilled
                    (cheapest real video — stretches free credits furthest;
                    set to fal-ai/wan/v2.2-a14b/text-to-video for max quality)
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from .base import ProviderBase
from .hf_video import LOCAL_PREFIX, copy_local_clip, local_job_status

TAG = "[fal_video]"

FAL_QUEUE_BASE = "https://queue.fal.run"
DEFAULT_MODEL = "fal-ai/ltxv-13b-098-distilled"
POLL_INTERVAL_SEC: float = 8.0
TIMEOUT_SEC: float = 480.0

_TERMINAL_FAIL_STATES = {"FAILED", "ERROR", "CANCELLED"}


def _log(msg: str, err: bool = False) -> None:
    """Print a tagged log line (stderr for errors)."""
    print(f"{TAG} {msg}", file=sys.stderr if err else sys.stdout)


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


class FalVideoProvider(ProviderBase):
    """Direct fal.ai queue video provider (one-time signup credits)."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("FAL_KEY", "")
        self.model: str = os.environ.get("FAL_VIDEO_MODEL", DEFAULT_MODEL)

    def is_connected(self) -> bool:
        """True if FAL_KEY is set."""
        return bool(self.api_key)

    def _request(self, url: str, payload: dict | None = None,
                 timeout: float = 120.0) -> dict:
        """GET/POST JSON against fal with Key auth. Returns JSON or {'error'}."""
        headers = {"Authorization": f"Key {self.api_key}",
                   "Content-Type": "application/json"}
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=body, headers=headers,
                                     method="POST" if payload is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": str(e), "code": e.code,
                    "body": e.read().decode("utf-8", errors="replace")[:500]}
        except Exception as e:
            return {"error": str(e), "code": 0}

    # ── Synchronous workhorse ──────────────────────────────────────────────
    def generate_clip(self, prompt: str, dest: Path,
                      aspect_ratio: str = "16:9") -> bool:
        """
        Submit → poll → download one clip to `dest`. Returns True on success.
        Retries once with a prompt-only payload if fal rejects extra params.
        """
        if not self.is_connected():
            return False
        submit_url = f"{FAL_QUEUE_BASE}/{self.model}"
        resp = self._request(submit_url, {"prompt": prompt,
                                          "aspect_ratio": aspect_ratio})
        if resp.get("code") == 422:
            _log(f"{self.model}: 422 on full payload, retrying prompt-only")
            resp = self._request(submit_url, {"prompt": prompt})
        if "error" in resp or not resp.get("request_id"):
            _log(f"{self.model}: submit failed — "
                 f"{str(resp.get('body', resp.get('error', resp)))[:200]}", err=True)
            return False
        status_url = str(resp.get("status_url", ""))
        response_url = str(resp.get("response_url", ""))
        _log(f"{self.model}: queued ({resp['request_id']}), polling...")
        deadline = time.monotonic() + TIMEOUT_SEC
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_SEC)
            status = self._request(status_url)
            state = str(status.get("status", "")).upper()
            if state == "COMPLETED":
                result = self._request(response_url)
                video = result.get("video")
                video_url = video.get("url") if isinstance(video, dict) else None
                if not video_url:
                    _log(f"{self.model}: completed but no video url — "
                         f"{str(result)[:200]}", err=True)
                    return False
                return super().download_clip(str(video_url), dest) \
                    and dest.exists() and dest.stat().st_size > 10_000
            if state in _TERMINAL_FAIL_STATES or status.get("code") in (401, 402, 403):
                _log(f"{self.model}: job failed — {str(status)[:200]}", err=True)
                return False
        _log(f"{self.model}: timed out after {TIMEOUT_SEC:.0f}s", err=True)
        return False

    # ── ProviderBase interface (waterfall-compatible) ──────────────────────
    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """Run text-to-video synchronously; return a `local:` pseudo-job."""
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        dest = Path(tempfile.gettempdir()) / f"fal_video_{abs(hash(prompt)) % 10**8}.mp4"
        if self.generate_clip(prompt, dest, aspect_ratio):
            return {"status": "submitted", "job_id": f"{LOCAL_PREFIX}{dest}",
                    "provider": "fal_video", "model": self.model}
        return {"status": "error", "job_id": None, "provider": "fal_video",
                "raw": f"{self.model} failed"}

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Not wired — Gemini/Pollinations handle images in this pipeline."""
        return {"status": "not_supported", "message": "Use gemini_image/Pollinations."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported — Kokoro handles all narration."""
        return {"status": "not_supported", "message": "Kokoro is the pipeline voice engine."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "No music support."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "No SFX support."}

    def get_job_status(self, job_id: str) -> dict:
        """Synchronous provider — jobs are `local:` pseudo-jobs, done on return."""
        if job_id.startswith(LOCAL_PREFIX):
            return local_job_status(job_id, "fal_video")
        return {"job_id": job_id, "status": "failed", "provider": "fal_video",
                "message": "Unknown job id (fal_video jobs are synchronous)."}

    def download_clip(self, output_url: str, dest_path: str | Path) -> bool:
        """Handle file:/// pseudo-URLs from the synchronous path."""
        if output_url.startswith("file:///"):
            return copy_local_clip(output_url, dest_path)
        return super().download_clip(output_url, dest_path)
