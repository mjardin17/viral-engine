"""
providers/waterfall.py

Free-first provider waterfall for LO/IL scene generation.

Order (free → paid):
  1. luma_ai        — LUMA_API_KEY            (video)
  2. fal_video      — FAL_KEY                 (video; one-time signup credits)
  3. hf_video       — HF_TOKEN                (video; HF monthly free credits,
                                               Wan2.2 → HunyuanVideo → LTX)
  4. pika           — PIKA_API_KEY            (video)
  5. minimax        — MINIMAX_API_KEY         (video)
  6. replicate      — REPLICATE_API_TOKEN     (video, open-source models)
  7. image_to_video — HF_TOKEN + GEMINI_API_KEY (free still → REAL MOTION clip;
                                               best free fallback)
  8. gemini_image   — GEMINI_API_KEY          (image → Ken Burns; free 500/day)
  9. pollinations   — no key needed           (image → Ken Burns; always free)
 10. higgsfield     — HIGGSFIELD_API_KEY      (video; PAID — absolute last resort)

Each provider is skipped silently if its key is missing, and skipped with a
log line if it errors or times out. This module never raises.

Usage (from empire_render.py):
    from providers.waterfall import generate_scene_asset
    asset = generate_scene_asset(prompt, duration_sec, "16:9", work_dir, "scene_03")
    if asset and asset.kind == "video":  ... fit to narration ...
    if asset and asset.kind == "image":  ... Ken Burns ...
"""

from __future__ import annotations

import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .base import ProviderBase

TAG = "[waterfall]"

POLL_INTERVAL_SEC: float = 10.0
POLL_TIMEOUT_SEC: float = 600.0

_TERMINAL_OK = {"completed", "succeeded", "success", "done", "finished"}
_TERMINAL_FAIL = {"failed", "error", "canceled", "cancelled", "rejected", "not_connected"}


@dataclass(frozen=True)
class SceneAsset:
    """A generated scene asset: either a video clip or a still image."""

    kind: str        # "video" | "image"
    path: Path       # local file on disk (verified >10KB)
    provider: str    # provider name for logging


def _log(msg: str, err: bool = False) -> None:
    """Print a tagged log line (stderr for errors)."""
    print(f"{TAG} {msg}", file=sys.stderr if err else sys.stdout)


# ── Video providers ────────────────────────────────────────────────────────────
def _run_video_provider(provider: ProviderBase, name: str, prompt: str,
                        duration_sec: int, aspect_ratio: str, dest: Path) -> Path | None:
    """
    Full lifecycle for one async video provider: submit → poll → download.
    Returns the downloaded clip path or None. Never raises.
    """
    try:
        if not provider.is_connected():
            return None  # silent skip — key not set
        job = provider.generate_video(prompt, aspect_ratio=aspect_ratio,
                                      duration_sec=duration_sec)
        if job.get("status") != "submitted" or not job.get("job_id"):
            _log(f"{name}: submit failed — {str(job.get('raw', ''))[:200]}", err=True)
            return None
        job_id = str(job["job_id"])
        _log(f"{name}: job {job_id} submitted, polling...")
        deadline = time.monotonic() + POLL_TIMEOUT_SEC
        while time.monotonic() < deadline:
            status = provider.get_job_status(job_id)
            state = str(status.get("status", "")).lower()
            if state in _TERMINAL_OK:
                url = status.get("output_url")
                if url and provider.download_clip(str(url), dest) \
                        and dest.exists() and dest.stat().st_size > 10_000:
                    return dest
                _log(f"{name}: completed but download failed", err=True)
                return None
            if state in _TERMINAL_FAIL:
                _log(f"{name}: job {state}", err=True)
                return None
            time.sleep(POLL_INTERVAL_SEC)
        _log(f"{name}: timed out after {POLL_TIMEOUT_SEC:.0f}s", err=True)
        return None
    except Exception as e:
        _log(f"{name}: unexpected error — {e}", err=True)
        return None


# ── Image providers ────────────────────────────────────────────────────────────
def _gemini_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """Generate a still via Gemini (free 500/day). Returns path or None."""
    try:
        from .gemini_image import GeminiImageProvider
        provider = GeminiImageProvider()
        if provider.is_connected() and provider.generate_image_file(prompt, dest, aspect_ratio):
            return dest
    except Exception as e:
        _log(f"gemini_image: unexpected error — {e}", err=True)
    return None


def _pollinations_image(prompt: str, dest: Path) -> Path | None:
    """Generate a still via Pollinations (always free, no key). Returns path or None."""
    encoded = urllib.parse.quote(prompt[:200])
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1920&height=1080&nologo=true"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        if len(data) > 10_000:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return dest
    except Exception as e:
        _log(f"pollinations: failed — {e}", err=True)
    return None


# ── Provider registry ──────────────────────────────────────────────────────────
def _video_chain() -> list[tuple[str, Callable[[], ProviderBase]]]:
    """Free video providers in waterfall order (lazy factories)."""
    from .fal_video import FalVideoProvider
    from .hf_video import HFVideoProvider
    from .image_to_video import ImageToVideoProvider
    from .luma import LumaProvider
    from .minimax import MinimaxProvider
    from .pika import PikaProvider
    from .replicate_video import ReplicateVideoProvider
    return [
        ("luma_ai", LumaProvider),
        ("fal_video", FalVideoProvider),          # one-time fal signup credits
        ("hf_video", HFVideoProvider),            # HF free monthly credits
        ("pika", PikaProvider),
        ("minimax", MinimaxProvider),
        ("replicate", ReplicateVideoProvider),
        ("image_to_video", ImageToVideoProvider), # free still → real motion
    ]


def _higgsfield() -> tuple[str, Callable[[], ProviderBase]]:
    """Higgsfield — PAID, last resort only."""
    from .higgsfield import HiggssfieldProvider
    return ("higgsfield", HiggssfieldProvider)


# ── Public API ─────────────────────────────────────────────────────────────────
def generate_scene_asset(prompt: str, duration_sec: int, aspect_ratio: str,
                         work_dir: Path, scene_tag: str) -> SceneAsset | None:
    """
    Run the full free-first waterfall for one scene.

    Returns a SceneAsset ("video" or "image") or None if every provider —
    including paid Higgsfield — failed. Never raises.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1-7. Free/cheap video providers (image_to_video = free REAL-MOTION fallback)
    for name, factory in _video_chain():
        try:
            provider = factory()
            if not provider.is_connected():
                continue
        except Exception as e:
            _log(f"{name}: init failed — {e}", err=True)
            continue
        dest = work_dir / f"{scene_tag}_{name}.mp4"
        clip = _run_video_provider(provider, name, prompt, duration_sec, aspect_ratio, dest)
        if clip:
            _log(f"{scene_tag} → {name} ✅")
            return SceneAsset(kind="video", path=clip, provider=name)

    # 8. Gemini image → Ken Burns (free 500/day)
    img = work_dir / f"{scene_tag}_gemini.png"
    if _gemini_image(prompt, img, aspect_ratio):
        _log(f"{scene_tag} → gemini_image (Ken Burns still) ✅")
        return SceneAsset(kind="image", path=img, provider="gemini_image")

    # 9. Pollinations image → Ken Burns (always free)
    img = work_dir / f"{scene_tag}_pollinations.jpg"
    if _pollinations_image(prompt, img):
        _log(f"{scene_tag} → pollinations (Ken Burns still) ✅")
        return SceneAsset(kind="image", path=img, provider="pollinations")

    # 10. Higgsfield — PAID, only when everything free has failed
    name, factory = _higgsfield()
    try:
        provider = factory()
        if provider.is_connected():
            _log("all free providers failed — falling back to PAID Higgsfield", err=True)
            dest = work_dir / f"{scene_tag}_{name}.mp4"
            clip = _run_video_provider(provider, name, prompt, duration_sec, aspect_ratio, dest)
            if clip:
                return SceneAsset(kind="video", path=clip, provider=name)
    except Exception as e:
        _log(f"{name}: init failed — {e}", err=True)

    _log(f"{scene_tag}: EVERY provider failed — scene has no visual", err=True)
    return None
