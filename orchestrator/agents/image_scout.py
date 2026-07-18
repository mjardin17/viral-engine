"""
orchestrator/agents/image_scout.py — Multi-source parallel image scout.

Given one image prompt, hits ALL sources IN PARALLEL and returns every
successful result ranked by quality (file size, largest first):

  Source 1: Wikimedia Commons API   (real historical photos — GG gold standard)
  Source 2: Pollinations AI         (always works, no key)
  Source 3: Gemini image generation (GEMINI_API_KEY in .env — free 500/day)

Usage:
    from orchestrator.agents.image_scout import scout_image
    results = scout_image("Battle of Cannae Roman legion", work_dir, "scene_03_img1")
    best = results[0]  # ImageResult(path, source, size_kb)

Never raises — a source that fails is simply absent from the results.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

TAG = "[image_scout]"
MAX_WORKERS = 4
MIN_VALID_BYTES = 10_000


@dataclass(frozen=True)
class ImageResult:
    """One successfully fetched/generated image."""

    path: Path
    source: str   # "wikimedia" | "pollinations" | "gemini"
    size_kb: int


def _log(msg: str) -> None:
    """Tagged stdout log line."""
    print(f"{TAG} {msg}", flush=True)


# ── Individual sources (each returns Path or None, never raises) ──────────────
def _try_wikimedia(prompt: str, dest: Path) -> Optional[Path]:
    """Source 1: Wikimedia Commons (validated real JPEG/PNG >50KB)."""
    try:
        from empire_render import fetch_wikimedia_image
        if fetch_wikimedia_image(prompt, dest):
            return dest
    except Exception as e:
        _log(f"wikimedia failed: {e}")
    return None


def _try_pollinations(prompt: str, dest: Path) -> Optional[Path]:
    """Source 2: Pollinations AI (free, keyless)."""
    try:
        from empire_render import fetch_pollinations_image
        if fetch_pollinations_image(prompt, dest):
            return dest
    except Exception as e:
        _log(f"pollinations failed: {e}")
    return None


def _try_gemini(prompt: str, dest: Path) -> Optional[Path]:
    """Source 3: Gemini image generation (needs GEMINI_API_KEY)."""
    try:
        from providers.gemini_image import GeminiImageProvider
        provider = GeminiImageProvider()
        if provider.is_connected() and provider.generate_image_file(prompt, dest, "16:9"):
            if dest.exists() and dest.stat().st_size > MIN_VALID_BYTES:
                return dest
    except Exception as e:
        _log(f"gemini failed: {e}")
    return None


_SOURCES: list[tuple[str, Callable[[str, Path], Optional[Path]], str]] = [
    ("wikimedia", _try_wikimedia, ".jpg"),
    ("pollinations", _try_pollinations, ".jpg"),
    ("gemini", _try_gemini, ".png"),
]


# ── Public API ────────────────────────────────────────────────────────────────
def scout_image(prompt: str, work_dir: Path, tag: str,
                sources: Optional[list[str]] = None) -> list[ImageResult]:
    """
    Fetch `prompt` from every source in parallel.

    Args:
        prompt:   Image search/generation prompt.
        work_dir: Directory for downloaded files.
        tag:      Filename stem, e.g. "scene_03_img1" → scene_03_img1_wikimedia.jpg
        sources:  Optional subset of source names (default: all three).

    Returns:
        All successful ImageResults sorted by size_kb DESC (best first).
        Empty list if every source failed.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    active = [(n, fn, ext) for n, fn, ext in _SOURCES if sources is None or n in sources]

    results: list[ImageResult] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(fn, prompt, work_dir / f"{tag}_{name}{ext}"): name
            for name, fn, ext in active
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                path = future.result()
            except Exception as e:  # belt and braces — sources shouldn't raise
                _log(f"{name}: unexpected error — {e}")
                continue
            if path is not None and path.exists() and path.stat().st_size > MIN_VALID_BYTES:
                size_kb = path.stat().st_size // 1024
                _log(f"{tag} — {name} ✅ ({size_kb}KB)")
                results.append(ImageResult(path=path, source=name, size_kb=size_kb))

    results.sort(key=lambda r: r.size_kb, reverse=True)
    if not results:
        _log(f"{tag} — ALL sources failed for prompt: {prompt[:80]}")
    return results


def scout_best_image(prompt: str, work_dir: Path, tag: str) -> Optional[ImageResult]:
    """Convenience: return only the single best image (or None)."""
    results = scout_image(prompt, work_dir, tag)
    return results[0] if results else None
