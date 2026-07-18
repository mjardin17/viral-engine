"""
providers/openverse.py

Openverse (openverse.org) — 700M+ CC-licensed images. ZERO SIGNUP for
basic search (anonymous requests are rate-limited but always allowed).

  GET https://api.openverse.org/v1/images/
      ?q={query}&license_type=commercial&page_size=5
  → {"results": [{"url": ..., "title": ..., "license": ...}]}

api.openverse.org is the canonical host; api.openverse.engineering is the
legacy domain kept as a fallback. license_type=commercial keeps every
result safe for monetized YouTube.

All methods fail soft (return None / empty) — never raise.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Canonical host first; legacy .engineering domain as fallback.
API_URLS = (
    "https://api.openverse.org/v1/images/"
    "?q={query}&license_type=commercial&page_size=5",
    "https://api.openverse.engineering/v1/images/"
    "?q={query}&license_type=commercial&page_size=5",
)
MIN_IMAGE_BYTES = 15_000
LOG_TAG = "[openverse]"
UA = {"User-Agent": "EmpireOS/1.0 (Gods&Glory pipeline)"}


def _looks_like_image(path: Path) -> bool:
    """Magic-byte check: real JPEG or PNG file."""
    try:
        head = path.read_bytes()[:8]
    except OSError:
        return False
    return head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n")


class OpenverseProvider:
    """Openverse keyless CC-image search — commercial-licensed real photos."""

    def is_connected(self) -> bool:
        """Always True — anonymous queries need no key."""
        return True

    def search(self, query: str) -> list[dict]:
        """Search Openverse; returns result dicts (may be empty). Never raises."""
        for api_url in API_URLS:
            url = api_url.format(query=urllib.parse.quote(query[:200]))
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results") or []
                return [r for r in results if isinstance(r, dict) and r.get("url")]
            except urllib.error.HTTPError as e:
                print(f"{LOG_TAG} search HTTP {e.code} for '{query[:60]}' "
                      f"({url.split('/')[2]})", flush=True)
            except Exception as e:
                print(f"{LOG_TAG} search failed ({url.split('/')[2]}): {e}", flush=True)
        return []

    def fetch_image(self, prompt: str, dest: str | Path,
                    aspect_ratio: str = "16:9") -> Path | None:
        """
        Search + download the first usable Openverse image for `prompt`.
        Returns the written Path or None.
        """
        dest = Path(dest)
        for result in self.search(prompt):
            try:
                req = urllib.request.Request(str(result["url"]), headers=UA)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                if len(data) < MIN_IMAGE_BYTES:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                if _looks_like_image(dest):
                    title = str(result.get("title", ""))[:60]
                    print(f"{LOG_TAG} ✅ {title} ({len(data) // 1024}KB)", flush=True)
                    return dest
                dest.unlink(missing_ok=True)
            except Exception as e:
                print(f"{LOG_TAG} candidate download failed: {e}", flush=True)
        return None
