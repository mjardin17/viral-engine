"""
providers/wikiart.py

WikiArt — 250k+ historical paintings, ZERO SIGNUP, ZERO KEY.

  GET https://www.wikiart.org/en/search/{query}/1?json=2
  → list (or dict wrapping a list) of artworks with an image URL field.

Perfect for the GG documentary look: "ancient battle painting",
"Roman empire artwork", "medieval siege painting", etc. Public-domain-era
art, filtered for the highest-resolution candidates.

All methods fail soft (return None / empty) — never raise.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://www.wikiart.org/en/search/{query}/1?json=2"
MIN_IMAGE_BYTES = 20_000
MAX_CANDIDATES = 5
LOG_TAG = "[wikiart]"
UA = {"User-Agent": "EmpireOS/1.0 (Gods&Glory pipeline)"}
# Fields that may hold the artwork image URL across WikiArt response shapes.
IMAGE_FIELDS = ("image", "imageUrl", "img", "imageThumb")


def _looks_like_image(path: Path) -> bool:
    """Magic-byte check: real JPEG or PNG file."""
    try:
        head = path.read_bytes()[:8]
    except OSError:
        return False
    return head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n")


def _upscale_url(url: str) -> str:
    """
    WikiArt appends size modifiers like '!Large.jpg' / '!PinterestSmall.jpg'.
    Strip the modifier to request the original full-resolution file.
    """
    return re.sub(r"!(?:[A-Za-z]+)\.(jpg|jpeg|png)$", r".\1", url, flags=re.IGNORECASE)


class WikiArtProvider:
    """WikiArt keyless painting search — historical art for documentary scenes."""

    def is_connected(self) -> bool:
        """Always True — no key, no account, no signup."""
        return True

    def search(self, query: str) -> list[dict]:
        """Search WikiArt; returns artwork dicts (may be empty). Never raises."""
        url = API_URL.format(query=urllib.parse.quote(query[:150]))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"{LOG_TAG} search HTTP {e.code} for '{query[:60]}'", flush=True)
            return []
        except Exception as e:
            print(f"{LOG_TAG} search failed: {e}", flush=True)
            return []
        # Response shape has shifted over time: bare list, or a dict wrapper.
        if isinstance(data, list):
            artworks = data
        elif isinstance(data, dict):
            artworks = next((v for k, v in data.items()
                             if isinstance(v, list) and v
                             and isinstance(v[0], dict)), [])
        else:
            artworks = []
        return [a for a in artworks if isinstance(a, dict) and self._image_url(a)]

    @staticmethod
    def _image_url(artwork: dict) -> str | None:
        """Pull the first plausible image URL from an artwork record."""
        for field in IMAGE_FIELDS:
            value = artwork.get(field)
            if isinstance(value, str) and value.startswith("http"):
                return value
        return None

    def fetch_image(self, prompt: str, dest: str | Path,
                    aspect_ratio: str = "16:9") -> Path | None:
        """
        Search + download the best WikiArt painting for `prompt` to `dest`.
        Tries the full-resolution URL first, then the listed URL as-is.
        Returns the written Path or None.
        """
        dest = Path(dest)
        for artwork in self.search(prompt)[:MAX_CANDIDATES]:
            listed = self._image_url(artwork)
            if not listed:
                continue
            urls = [listed]
            full = _upscale_url(listed)
            if full != listed:
                urls.insert(0, full)  # highest resolution first
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers=UA)
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        data = resp.read()
                    if len(data) < MIN_IMAGE_BYTES:
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                    if _looks_like_image(dest):
                        title = str(artwork.get("title", ""))[:60]
                        print(f"{LOG_TAG} ✅ {title} ({len(data) // 1024}KB)", flush=True)
                        return dest
                    dest.unlink(missing_ok=True)
                except Exception as e:
                    print(f"{LOG_TAG} candidate download failed: {e}", flush=True)
        return None
