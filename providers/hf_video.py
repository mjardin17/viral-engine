"""
providers/hf_video.py

Hugging Face Inference Providers video generation — the best FREE real-video
option in the waterfall (HF_TOKEN is already in .env).

How it works (verified against huggingface_hub source, July 2026):
  * HF routes video tasks to partner providers (fal-ai, replicate, together)
    through https://router.huggingface.co, billed against the HF account's
    monthly included inference credits — no fal/replicate account needed.
  * The fal-ai route uses fal's queue protocol:
      1. POST https://router.huggingface.co/fal-ai/{providerId}?_subdomain=queue
         Authorization: Bearer hf_***       body: {"prompt": ...}
         → {"request_id", "response_url", "status_url", "status"}
      2. Poll  {router}/fal-ai{path(response_url)}/status?_subdomain=queue
         until status == "COMPLETED"
      3. GET   {router}/fal-ai{path(response_url)}?_subdomain=queue
         → {"video": {"url": ...}} → download the MP4.
  * The providerId for each HF model is resolved live from
    https://huggingface.co/api/models/{id}?expand[]=inferenceProviderMapping
    so stale/retired models are skipped automatically.

Live text-to-video models (checked 2026-07-16), tried in quality order:
  Wan-AI/Wan2.2-T2V-A14B                → fal-ai/wan/v2.2-a14b/text-to-video
  tencent/HunyuanVideo                  → fal-ai/hunyuan-video
  Lightricks/LTX-Video-0.9.8-13B-distilled → fal-ai/ltxv-13b-098-distilled

Live image-to-video models (used by providers/image_to_video.py):
  Wan-AI/Wan2.2-I2V-A14B                → fal-ai/wan/v2.2-a14b/image-to-video
  Lightricks/LTX-2                      → fal-ai/ltx-2-19b/distilled/image-to-video
  Wan-AI/Wan2.1-I2V-14B-720P            → fal-ai/wan-i2v
  Lightricks/LTX-Video-0.9.8-13B-distilled → fal-ai/ltxv-13b-098-distilled/image-to-video
  tencent/HunyuanVideo-I2V              → fal-ai/hunyuan-video-image-to-video

Honest quota note: HF free accounts get a small monthly included-credits
allowance (PRO accounts get more). When the allowance is exhausted the router
returns 402 and this provider steps aside — the waterfall moves on. That is
expected behaviour, not a bug.

Env:
  HF_TOKEN         (required — already set)
  HF_T2V_MODELS    optional comma-separated override of the T2V model list
  HF_I2V_MODELS    optional comma-separated override of the I2V model list
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .base import ProviderBase

TAG = "[hf_video]"

HF_ROUTER_FAL = "https://router.huggingface.co/fal-ai"
HF_MODEL_INFO = "https://huggingface.co/api/models/{model}?expand[]=inferenceProviderMapping"

# Quality order — best first. Resolved live at runtime; dead entries skip.
DEFAULT_T2V_MODELS: tuple[str, ...] = (
    "Wan-AI/Wan2.2-T2V-A14B",                   # best open-source quality
    "tencent/HunyuanVideo",                     # best motion
    "Lightricks/LTX-Video-0.9.8-13B-distilled", # fastest / cheapest
)
DEFAULT_I2V_MODELS: tuple[str, ...] = (
    "Wan-AI/Wan2.2-I2V-A14B",                   # best quality animation
    "Lightricks/LTX-2",                         # strong + fast (distilled)
    "Wan-AI/Wan2.1-I2V-14B-720P",
    "Lightricks/LTX-Video-0.9.8-13B-distilled",
    "tencent/HunyuanVideo-I2V",
)

# Verified-live fal routes (2026-07-16) — used when the Hub mapping API is
# unreachable (network hiccup) so one failed lookup can't kill the provider.
KNOWN_FAL_ROUTES: dict[tuple[str, str], str] = {
    ("Wan-AI/Wan2.2-T2V-A14B", "text-to-video"): "fal-ai/wan/v2.2-a14b/text-to-video",
    ("tencent/HunyuanVideo", "text-to-video"): "fal-ai/hunyuan-video",
    ("Lightricks/LTX-Video-0.9.8-13B-distilled", "text-to-video"):
        "fal-ai/ltxv-13b-098-distilled",
    ("Wan-AI/Wan2.2-I2V-A14B", "image-to-video"): "fal-ai/wan/v2.2-a14b/image-to-video",
    ("Lightricks/LTX-2", "image-to-video"): "fal-ai/ltx-2-19b/distilled/image-to-video",
    ("Wan-AI/Wan2.1-I2V-14B-720P", "image-to-video"): "fal-ai/wan-i2v",
    ("Lightricks/LTX-Video-0.9.8-13B-distilled", "image-to-video"):
        "fal-ai/ltxv-13b-098-distilled/image-to-video",
    ("tencent/HunyuanVideo-I2V", "image-to-video"): "fal-ai/hunyuan-video-image-to-video",
}

POLL_INTERVAL_SEC: float = 8.0
PER_MODEL_TIMEOUT_SEC: float = 480.0   # 8 min per model, then try the next one
LOCAL_PREFIX = "local:"                # pseudo job_id for synchronous results

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


# ── Local pseudo-job helpers (shared with image_to_video.py / fal_video.py) ──
def local_job_status(job_id: str, provider: str) -> dict:
    """Status dict for a `local:` pseudo-job — completed if the file exists."""
    local = job_id[len(LOCAL_PREFIX):]
    return {
        "job_id": job_id,
        "status": "completed" if Path(local).exists() else "failed",
        "output_url": f"file:///{local}",
        "local_path": local,
        "provider": provider,
    }


def copy_local_clip(output_url: str, dest_path: str | Path) -> bool:
    """Copy a file:/// pseudo-URL to dest_path. Returns True on success (>10KB)."""
    if not output_url.startswith("file:///"):
        return False
    src = Path(output_url[len("file:///"):])
    try:
        if src.exists() and src.stat().st_size > 10_000:
            dest = Path(dest_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            return True
    except Exception:
        pass
    return False


def image_to_data_uri(image_path: Path) -> str:
    """Encode a local image file as a base64 data URI for fal payloads."""
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ── HTTP helpers ───────────────────────────────────────────────────────────────
def _http_json(url: str, token: str, payload: dict | None = None,
               timeout: float = 120.0) -> dict:
    """GET/POST JSON with Bearer auth. Returns parsed JSON or {'error', 'code'}."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
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


def _download_url(url: str, dest: Path, token: str | None = None) -> bool:
    """Download a generated clip to dest. True if the file lands >10KB."""
    headers = {"User-Agent": "EmpireOS/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = resp.read()
        if len(data) < 10_000:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as e:
        _log(f"download failed — {e}", err=True)
        return False


# ── HF router (fal-ai queue) core ─────────────────────────────────────────────
def resolve_fal_provider_id(model_id: str, task: str) -> str | None:
    """
    Resolve the live fal-ai providerId for an HF model + task ("text-to-video"
    or "image-to-video") from the Hub inference-provider mapping. None if the
    model has no live fal-ai route for that task.
    """
    url = HF_MODEL_INFO.format(model=urllib.parse.quote(model_id))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            info = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        fallback = KNOWN_FAL_ROUTES.get((model_id, task))
        _log(f"{model_id}: mapping lookup failed ({e}) — "
             f"{'using verified fallback route' if fallback else 'no fallback route'}",
             err=True)
        return fallback
    mapping = info.get("inferenceProviderMapping") or {}
    # Mapping is a dict on single-model lookups, a list on search results.
    if isinstance(mapping, dict):
        entry = mapping.get("fal-ai") or {}
        if entry.get("status") == "live" and entry.get("task") == task:
            return str(entry.get("providerId"))
        return None
    for entry in mapping:
        if (entry.get("provider") == "fal-ai" and entry.get("status") == "live"
                and entry.get("task") == task):
            return str(entry.get("providerId"))
    return None


def run_fal_queue_job(provider_id: str, payload: dict, token: str, dest: Path,
                      timeout_sec: float = PER_MODEL_TIMEOUT_SEC) -> bool:
    """
    Full fal queue lifecycle via the HF router: submit → poll → fetch result →
    download video. Returns True when dest holds a valid clip. Never raises.
    On a 422 (payload validation), retries once with only the core keys.
    """
    submit_url = f"{HF_ROUTER_FAL}/{provider_id}?_subdomain=queue"
    resp = _http_json(submit_url, token, payload)
    if resp.get("code") == 422:
        core = {k: v for k, v in payload.items() if k in ("prompt", "image_url")}
        _log(f"{provider_id}: 422 on full payload, retrying with core keys only")
        resp = _http_json(submit_url, token, core)
    if "error" in resp:
        _log(f"{provider_id}: submit failed [{resp.get('code')}] "
             f"{str(resp.get('body', resp['error']))[:200]}", err=True)
        return False
    response_url = resp.get("response_url", "")
    if not resp.get("request_id") or not response_url:
        _log(f"{provider_id}: no request_id in response — {str(resp)[:200]}", err=True)
        return False
    path = urllib.parse.urlparse(response_url).path
    status_url = f"{HF_ROUTER_FAL}{path}/status?_subdomain=queue"
    result_url = f"{HF_ROUTER_FAL}{path}?_subdomain=queue"
    _log(f"{provider_id}: queued ({resp['request_id']}), polling up to "
         f"{timeout_sec:.0f}s...")
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SEC)
        status = _http_json(status_url, token)
        state = str(status.get("status", "")).upper()
        if state == "COMPLETED":
            result = _http_json(result_url, token)
            video_url = ((result.get("video") or {}).get("url")
                         if isinstance(result.get("video"), dict) else None)
            if not video_url:
                _log(f"{provider_id}: completed but no video url — "
                     f"{str(result)[:200]}", err=True)
                return False
            return _download_url(video_url, dest)
        if state in _TERMINAL_FAIL_STATES or status.get("code") in (402, 403, 404):
            _log(f"{provider_id}: job failed — {str(status)[:200]}", err=True)
            return False
    _log(f"{provider_id}: timed out after {timeout_sec:.0f}s", err=True)
    return False


def _models_from_env(var: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """Read a comma-separated model list override from the environment."""
    raw = os.environ.get(var, "").strip()
    if not raw:
        return default
    return tuple(m.strip() for m in raw.split(",") if m.strip())


class HFVideoProvider(ProviderBase):
    """Free video generation via HF Inference Providers (fal-ai route)."""

    def __init__(self) -> None:
        _load_env()
        self.token: str = os.environ.get("HF_TOKEN", "")
        self.t2v_models: tuple[str, ...] = _models_from_env("HF_T2V_MODELS",
                                                            DEFAULT_T2V_MODELS)
        self.i2v_models: tuple[str, ...] = _models_from_env("HF_I2V_MODELS",
                                                            DEFAULT_I2V_MODELS)

    def is_connected(self) -> bool:
        """True if HF_TOKEN is set."""
        return bool(self.token)

    # ── Synchronous workhorses ─────────────────────────────────────────────
    def generate_clip(self, prompt: str, dest: Path,
                      aspect_ratio: str = "16:9") -> str | None:
        """
        Text-to-video: try each T2V model in quality order until one delivers
        a clip to `dest`. Returns the winning HF model id, or None.
        """
        if not self.is_connected():
            return None
        for model in self.t2v_models:
            provider_id = resolve_fal_provider_id(model, "text-to-video")
            if not provider_id:
                _log(f"{model}: no live fal-ai text-to-video route, skipping")
                continue
            payload = {"prompt": prompt, "aspect_ratio": aspect_ratio}
            if run_fal_queue_job(provider_id, payload, self.token, dest):
                _log(f"{model} ✅ → {dest.name}")
                return model
        return None

    def animate_image(self, image_path: Path, prompt: str, dest: Path) -> str | None:
        """
        Image-to-video: animate a local still into a short clip. Tries each
        I2V model in quality order. Returns the winning HF model id, or None.
        """
        if not self.is_connected() or not image_path.exists():
            return None
        image_url = image_to_data_uri(image_path)
        for model in self.i2v_models:
            provider_id = resolve_fal_provider_id(model, "image-to-video")
            if not provider_id:
                _log(f"{model}: no live fal-ai image-to-video route, skipping")
                continue
            payload = {"image_url": image_url, "prompt": prompt}
            if run_fal_queue_job(provider_id, payload, self.token, dest):
                _log(f"{model} ✅ → {dest.name}")
                return model
        return None

    # ── ProviderBase interface (waterfall-compatible) ──────────────────────
    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """
        Run text-to-video (or image-to-video when a reference image is given)
        synchronously and return a `local:` pseudo-job pointing at the clip.
        """
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        dest = Path(tempfile.gettempdir()) / f"hf_video_{abs(hash(prompt)) % 10**8}.mp4"
        if reference_image_path and Path(reference_image_path).exists():
            model = self.animate_image(Path(reference_image_path), prompt, dest)
        else:
            model = self.generate_clip(prompt, dest, aspect_ratio)
        if model:
            return {"status": "submitted", "job_id": f"{LOCAL_PREFIX}{dest}",
                    "provider": "hf_video", "model": model}
        return {"status": "error", "job_id": None, "provider": "hf_video",
                "raw": "all HF video models failed"}

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Not wired — Gemini/Pollinations handle images in this pipeline."""
        return {"status": "not_supported", "message": "Use gemini_image/Pollinations."}

    def generate_audio(self, prompt: str, voice: str = "Hades", duration_sec: int = 10) -> dict:
        """Not supported — Kokoro handles all narration."""
        return {"status": "not_supported", "message": "Kokoro is the pipeline voice engine."}

    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "Music not wired via HF."}

    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Not supported."""
        return {"status": "not_supported", "message": "SFX not wired via HF."}

    def get_job_status(self, job_id: str) -> dict:
        """Synchronous provider — jobs are `local:` pseudo-jobs, done on return."""
        if job_id.startswith(LOCAL_PREFIX):
            return local_job_status(job_id, "hf_video")
        return {"job_id": job_id, "status": "failed", "provider": "hf_video",
                "message": "Unknown job id (hf_video jobs are synchronous)."}

    def download_clip(self, output_url: str, dest_path: str | Path) -> bool:
        """Handle file:/// pseudo-URLs from the synchronous path."""
        if output_url.startswith("file:///"):
            return copy_local_clip(output_url, dest_path)
        return super().download_clip(output_url, dest_path)
