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

  Image chain (each → Ken Burns still; ZERO-SIGNUP sources first):
  8.  wikimedia        — no key needed        (real historical photos, public domain)
  9.  wikiart          — no key needed        (historical paintings, public domain)
 10.  openverse        — no key needed        (700M+ CC commercial-licensed images)
 11.  lexica           — no key needed        (HD AI-image search, any prompt)
 12.  gemini_image     — GEMINI_API_KEY       (AI gen; free 500/day)
 12b. cloudflare_image — CF_ACCOUNT_ID+CF_API_TOKEN (AI gen; free 10k/day)
 13.  pollinations     — no key needed        (AI gen; always free)
 14.  ai_horde         — no key needed        (anonymous crowdsourced SD,
                                               slow queue but always free)
 15.  picsum           — no key needed        (LAST RESORT random placeholder —
                                               unrelated to prompt, beats black frame)
 16.  higgsfield       — HIGGSFIELD_API_KEY   (video; PAID — absolute last resort)

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


def paid_credit_warning(seconds: int = 10, context: str = "Higgsfield") -> None:
    """Shared 10-second Ctrl+C credit-guard warning — Higgsfield credits are
    real money. ADDITIVE: extracted so new callers (episode_credit_planner.py)
    can reuse the exact same guard instead of duplicating it a third time.
    The inline warnings below (in this module) and in higgsfield_adapter.py
    are left untouched for safety — this is a new, equivalent helper."""
    _log(f"⚠️ WARNING: about to use {context} (PAID). "
         f"Press Ctrl+C within {seconds} seconds to cancel.", err=True)
    time.sleep(seconds)
    _log(f"no cancel — proceeding with PAID {context}", err=True)


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
def _wikimedia_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """Fetch a real historical photo from Wikimedia Commons (no key)."""
    try:
        from empire_render import fetch_wikimedia_image
        if fetch_wikimedia_image(prompt, dest):
            return dest
    except Exception as e:
        _log(f"wikimedia: unexpected error — {e}", err=True)
    return None


def _wikiart_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """Fetch a historical painting from WikiArt (no key, public domain era art)."""
    try:
        from .wikiart import WikiArtProvider
        return WikiArtProvider().fetch_image(prompt, dest, aspect_ratio)
    except Exception as e:
        _log(f"wikiart: unexpected error — {e}", err=True)
    return None


def _openverse_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """Fetch a CC commercial-licensed image from Openverse (no key)."""
    try:
        from .openverse import OpenverseProvider
        return OpenverseProvider().fetch_image(prompt, dest, aspect_ratio)
    except Exception as e:
        _log(f"openverse: unexpected error — {e}", err=True)
    return None


def _lexica_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """Fetch an HD AI-generated image from Lexica search (no key)."""
    try:
        from .lexica_search import LexicaProvider
        return LexicaProvider().fetch_image(prompt, dest, aspect_ratio)
    except Exception as e:
        _log(f"lexica: unexpected error — {e}", err=True)
    return None


def _picsum_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """LAST RESORT: random scenic placeholder from Lorem Picsum (no key)."""
    try:
        from .picsum import PicsumProvider
        return PicsumProvider().fetch_image(prompt, dest, aspect_ratio)
    except Exception as e:
        _log(f"picsum: unexpected error — {e}", err=True)
    return None


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


def _cloudflare_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """Generate a still via Cloudflare Workers AI FLUX-schnell (free 10k/day)."""
    try:
        from .cloudflare_image import CloudflareImageProvider
        provider = CloudflareImageProvider()
        if provider.is_connected() and provider.generate_image_file(prompt, dest, aspect_ratio):
            return dest
    except Exception as e:
        _log(f"cloudflare_image: unexpected error — {e}", err=True)
    return None


def _ai_horde_image(prompt: str, dest: Path, aspect_ratio: str) -> Path | None:
    """Generate a still via AI Horde (anonymous key, always free, slow queue)."""
    try:
        from .ai_horde import AIHordeProvider
        provider = AIHordeProvider()
        if provider.generate_image_file(prompt, dest, aspect_ratio):
            return dest
    except Exception as e:
        _log(f"ai_horde: unexpected error — {e}", err=True)
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

    # 8-15. Image chain → Ken Burns. ZERO-SIGNUP real sources first
    # (Wikimedia photos → WikiArt paintings → Openverse CC → Lexica AI search),
    # then keyed AI gen (Gemini/Cloudflare), then keyless AI gen (Pollinations
    # → AI Horde), then the Picsum LAST-RESORT placeholder.
    image_chain: list[tuple[str, Callable[[str, Path, str], Path | None], str]] = [
        ("wikimedia", _wikimedia_image, ".jpg"),
        ("wikiart", _wikiart_image, ".jpg"),
        ("openverse", _openverse_image, ".jpg"),
        ("lexica", _lexica_image, ".jpg"),
        ("gemini_image", _gemini_image, ".png"),
        ("cloudflare_image", _cloudflare_image, ".jpg"),
        ("pollinations", lambda p, d, _ar: _pollinations_image(p, d), ".jpg"),
        ("ai_horde", _ai_horde_image, ".png"),
        ("picsum", _picsum_image, ".jpg"),  # LAST RESORT — unrelated placeholder
    ]
    for name, fetch, ext in image_chain:
        img = work_dir / f"{scene_tag}_{name}{ext}"
        if fetch(prompt, img, aspect_ratio) and img.exists() \
                and img.stat().st_size > 10_000:
            _log(f"{scene_tag} → {name} (Ken Burns still) ✅")
            return SceneAsset(kind="image", path=img, provider=name)

    # 16. Higgsfield — PAID, only when everything free has failed
    name, factory = _higgsfield()
    try:
        provider = factory()
        if provider.is_connected():
            # Credit guard — Higgsfield credits are real money. Give Josh a
            # 10-second window to abort before any paid call is made.
            _log("⚠️ WARNING: All free providers failed. About to use Higgsfield "
                 "(PAID). Press Ctrl+C within 10 seconds to cancel.", err=True)
            time.sleep(10)
            _log("no cancel — proceeding with PAID Higgsfield", err=True)
            dest = work_dir / f"{scene_tag}_{name}.mp4"
            clip = _run_video_provider(provider, name, prompt, duration_sec, aspect_ratio, dest)
            if clip:
                return SceneAsset(kind="video", path=clip, provider=name)
    except Exception as e:
        _log(f"{name}: init failed — {e}", err=True)

    _log(f"{scene_tag}: EVERY provider failed — scene has no visual", err=True)
    return None
