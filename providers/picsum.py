"""
providers/picsum.py

Lorem Picsum — random scenic HD photos, ZERO SIGNUP, ZERO KEY.

  GET https://picsum.photos/1920/1080 → redirects to a random HD photo.

⚠️ LAST_RESORT ONLY. These photos are NOT related to the prompt — they are
generic scenery. This provider exists purely so a scene ships with *some*
visual instead of a black screen (bot_10_frame_inspector fails black
frames), and only after every real free provider has been exhausted and
before any PAID call.

All methods fail soft (return None) — never raise.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

LAST_RESORT = True  # waterfall checks this flag — never promote this provider
PHOTO_URL = "https://picsum.photos/1920/1080"
MIN_IMAGE_BYTES = 20_000
LOG_TAG = "[picsum]"
UA = {"User-Agent": "EmpireOS/1.0"}


class PicsumProvider:
    """Lorem Picsum placeholder photos — the absolute last free fallback."""

    def is_connected(self) -> bool:
        """Always True — no key, no account, no signup."""
        return True

    def fetch_image(self, prompt: str, dest: str | Path,
                    aspect_ratio: str = "16:9") -> Path | None:
        """
        Download one random 1920x1080 photo to `dest`. The prompt is ignored
        (Picsum has no search) — this is a placeholder, not a match.
        Returns the written Path or None.
        """
        dest = Path(dest)
        try:
            req = urllib.request.Request(PHOTO_URL, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) < MIN_IMAGE_BYTES:
                print(f"{LOG_TAG} response too small ({len(data)} bytes)", flush=True)
                return None
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            print(f"{LOG_TAG} ⚠ LAST-RESORT placeholder used "
                  f"({len(data) // 1024}KB) — unrelated to prompt", flush=True)
            return dest
        except Exception as e:
            print(f"{LOG_TAG} failed: {e}", flush=True)
            return None
