"""
providers/image_to_video.py

The GUARANTEED-FREE motion fallback: generate a still image with Gemini
(free ~500/day, key already set) or Pollinations (always free, no key),
then animate it into a real 5-6 second motion clip via HF Inference
Providers image-to-video (HF_TOKEN, already set).

Chain:
  1. gemini_image.generate_image_file()   — free 500/day
     └ fallback: Pollinations image        — always free, no key
  2. HFVideoProvider.animate_image()       — Wan2.2-I2V → LTX-2 → Wan2.1-I2V
     → LTXV-distilled → HunyuanVideo-I2V (first live model wins)

This produces ACTUAL MOTION (not a Ken Burns pan over a frozen frame) —
the biggest free quality upgrade available for LO/IL cartoon scenes.

If step 2 fails (HF monthly credits exhausted, all I2V routes down), the
waterfall still has the plain Gemini/Pollinations Ken Burns path after
this provider, so nothing is lost by trying.

Env: GEMINI_API_KEY (set), HF_TOKEN (set). Nothing new needed.
"""

from __future__ import annotations

import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from .base import ProviderBase
from .hf_video import LOCAL_PREFIX, HFVideoProvider, copy_local_clip, local_job_status

TAG = "[image_to_video]"


def _log(msg: str, err: bool = False) -> None:
    """Print a tagged log line (stderr for errors)."""
    print(f"{TAG} {msg}", file=sys.stderr if err else sys.stdout)


def _generate_still(prompt: str, dest: Path, aspect_ratio: str) -> str | None:
    """
    Generate the source still: Gemini first, Pollinations as backup.
    Returns the image-source name ("gemini" | "pollinations") or None.
    """
    try:
        from .gemini_image import GeminiImageProvider
        gemini = GeminiImageProvider()
        if gemini.is_connected() and gemini.generate_image_file(prompt, dest, aspect_ratio):
            return "gemini"
    except Exception as e:
        _log(f"gemini still failed — {e}", err=True)
    # Pollinations fallback — always free, no key
    w, h = (1920, 1080) if aspect_ratio != "9:16" else (1080, 1920)
    encoded = urllib.parse.quote(prompt[:200])
    url = (f"https://image.pollinations.ai/prompt/{encoded}"
           f"?width={w}&height={h}&nologo=true")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EmpireOS/1.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        if len(data) > 10_000:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return "pollinations"
    except Exception as e:
        _log(f"pollinations still failed — {e}", err=True)
    return None


class ImageToVideoProvider(ProviderBase):
    """Free image → motion-video provider (Gemini/Pollinations still + HF I2V)."""

    def __init__(self) -> None:
        self._hf = HFVideoProvider()

    def is_connected(self) -> bool:
        """True if HF_TOKEN is set (the animation step is the hard requirement)."""
        return self._hf.is_connected()

    # ── Synchronous workhorse ──────────────────────────────────────────────
    def generate_clip(self, prompt: str, dest: Path,
                      aspect_ratio: str = "16:9") -> str | None:
        """
        Still → animated clip. Returns "{image_source}+{i2v_model}" on success
        (e.g. "gemini+Wan-AI/Wan2.2-I2V-A14B"), or None. Never raises.
        """
        try:
            still = dest.with_suffix(".src.png")
            source = _generate_still(prompt, still, aspect_ratio)
            if not source:
                _log("no still image could be generated", err=True)
                return None
            motion_prompt = (f"{prompt}. Smooth cinematic camera motion, "
                             f"natural animated movement, high detail.")
            model = self._hf.animate_image(still, motion_prompt, dest)
            if model:
                _log(f"{source} still + {model} animation ✅ → {dest.name}")
                return f"{source}+{model}"
            _log("still generated but every I2V model failed", err=True)
        except Exception as e:
            _log(f"unexpected error — {e}", err=True)
        return None

    # ── ProviderBase interface (waterfall-compatible) ──────────────────────
    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """
        Full still→motion pipeline, synchronous. If a reference image is
        supplied it is animated directly (skipping still generation).
        Returns a `local:` pseudo-job pointing at the finished clip.
        """
        if not self.is_connected():
            return self.not_connected_response("generate_video")
        dest = Path(tempfile.gettempdir()) / f"i2v_{abs(hash(prompt)) % 10**8}.mp4"
        if reference_image_path and Path(reference_image_path).exists():
            model = self._hf.animate_image(Path(reference_image_path), prompt, dest)
        else:
            model = self.generate_clip(prompt, dest, aspect_ratio)
        if model:
            return {"status": "submitted", "job_id": f"{LOCAL_PREFIX}{dest}",
                    "provider": "image_to_video", "model": str(model)}
        return {"status": "error", "job_id": None, "provider": "image_to_video",
                "raw": "still→motion chain failed"}

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Not wired — this provider outputs video; use gemini_image for stills."""
        return {"status": "not_supported", "message": "Video-only provider."}

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
            return local_job_status(job_id, "image_to_video")
        return {"job_id": job_id, "status": "failed", "provider": "image_to_video",
                "message": "Unknown job id (image_to_video jobs are synchronous)."}

    def download_clip(self, output_url: str, dest_path: str | Path) -> bool:
        """Handle file:/// pseudo-URLs from the synchronous path."""
        if output_url.startswith("file:///"):
            return copy_local_clip(output_url, dest_path)
        return super().download_clip(output_url, dest_path)
