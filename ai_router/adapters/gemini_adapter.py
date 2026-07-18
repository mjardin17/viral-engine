"""
gemini_adapter.py — wraps EXISTING Gemini code (no duplication).

- IMAGE_GENERATION → providers.gemini_image.GeminiImageProvider.generate_image_file
- text tasks       → empire_render._gemini_generate_text (existing helper)
Uses GEMINI_API_KEY via the provider's own _load_env().
"""

from __future__ import annotations

import sys
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult, env

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

TEXT_TASKS = {"PLANNING", "WRITING", "STORYBOARDING", "PROMPT_CREATION"}


class GeminiAdapter(AdapterBase):
    """Gemini text + image generation — delegates to existing pipeline code."""

    name = "gemini"
    capability_score = 0.85
    default_cost_usd = 0.0  # free tier (500 images/day)

    def is_connected(self) -> bool:
        if env("GEMINI_API_KEY"):
            return True
        try:
            from providers.gemini_image import GeminiImageProvider
            return GeminiImageProvider().is_connected()
        except Exception:
            return False

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="GEMINI_API_KEY not set")
        task = payload.get("task_type", "")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")
        try:
            if task in TEXT_TASKS:
                from empire_render import _gemini_generate_text  # existing helper
                text, ms = self._timed(_gemini_generate_text, prompt)
                if text:
                    return AdapterResult(success=True, output=text, latency_ms=ms)
                return AdapterResult(success=False, error="Gemini returned no text",
                                     latency_ms=ms)
            # image generation / editing-adjacent → existing provider
            from providers.gemini_image import GeminiImageProvider
            dest = Path(payload.get("dest") or "gemini_image.png")
            aspect = str(payload.get("aspect_ratio", "16:9"))
            provider = GeminiImageProvider()
            ok, ms = self._timed(provider.generate_image_file, prompt, dest, aspect)
            if ok and dest.exists() and dest.stat().st_size > 10_000:
                return AdapterResult(success=True, output=str(dest), latency_ms=ms)
            return AdapterResult(success=False, error="Gemini image gen failed",
                                 latency_ms=ms)
        except Exception as e:
            return AdapterResult(success=False, error=f"gemini: {e}")
