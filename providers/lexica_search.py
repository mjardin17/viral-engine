"""
providers/lexica_search.py

Lexica.art — search engine for AI-generated images. ZERO SIGNUP, ZERO KEY:
the public search API returns real HD images for any prompt.

  GET https://lexica.art/api/v1/search?q={prompt}
  → {"images": [{"src": url, "prompt": ..., "width": ..., "height": ...}]}

Great for historical scenes ("ancient Roman battle legions", "Persian
soldiers Thermopylae"). Downloads the first usable result as a JPEG.

All methods fail soft (return None / False) — never raise.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://lexica.art/api/v1/search?q={query}"
MIN_IMAGE_BYTES = 10_000
MAX_CANDIDATES = 5
LOG_TAG = "[lexica]"
UA = {"User-Agent": "EmpireOS/1.0 (Gods&Glory pipeline)"}


def _looks_like_image(path: Path) -> bool:
    """Magic-byte check: real JPEG, PNG or WEBP file."""
    try:
        head = path.read_bytes()[:12]
    except OSError:
        return False
    return (head.startswith(b"\xff\xd8\xff")
            or head.startswith(b"\x89PNG\r\n\x1a\n")
            or head[:4] == b"RIFF" and head[8:12] == b"WEBP")


class LexicaProvider:
    """Lexica.art keyless image search — HD AI images for any prompt."""

    def is_connected(self) -> bool:
        """Always True — no key, no account, no signup."""
        return True

    def search(self, prompt: str) -> list[dict]:
        """Search Lexica; returns the images list (may be empty). Never raises."""
        url = API_URL.format(query=urllib.parse.quote(prompt[:300]))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            images = data.get("images") or []
            return [i for i in images if isinstance(i, dict) and i.get("src")]
        except urllib.error.HTTPError as e:
            print(f"{LOG_TAG} search HTTP {e.code} for '{prompt[:60]}'", flush=True)
        except Exception as e:
            print(f"{LOG_TAG} search failed: {e}", flush=True)
        return []

    def fetch_image(self, prompt: str, dest: str | Path,
                    aspect_ratio: str = "16:9") -> Path | None:
        """
        Search + download the best Lexica image for `prompt` to `dest`.
        Prefers larger images. Returns the written Path or None.
        """
        dest = Path(dest)
        candidates = self.search(prompt)
        # Bigger = better source material for Ken Burns zooms.
        candidates.sort(key=lambda i: -(int(i.get("width") or 0) * int(i.get("height") or 0)))
        for img in candidates[:MAX_CANDIDATES]:
            try:
                req = urllib.request.Request(str(img["src"]), headers=UA)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                if len(data) < MIN_IMAGE_BYTES:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                if _looks_like_image(dest):
                    print(f"{LOG_TAG} ✅ {len(data) // 1024}KB "
                          f"({img.get('width')}x{img.get('height')})", flush=True)
                    return dest
                dest.unlink(missing_ok=True)
            except Exception as e:
                print(f"{LOG_TAG} candidate download failed: {e}", flush=True)
        return None
