"""
wikimedia_fetch.py — Fetch real historical images from Wikimedia Commons
Part of the Gods & Glory upgraded pipeline (v3.0)

Usage:
    python wikimedia_fetch.py --query "Battle of Thermopylae" --out images/scene_01.jpg --count 3
"""

import argparse
import os
import urllib.request
import urllib.parse
import urllib.error
import json
import sys


WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "EmpireOS/1.0 (Gods&Glory pipeline; contact@empireos.ai)"


def search_wikimedia(query: str, count: int = 5) -> list[dict]:
    """Search Wikimedia Commons for images matching query."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",  # File namespace
        "gsrsearch": f"{query} historical painting battle",
        "gsrlimit": count * 3,  # Fetch extra to filter
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": "1920",
        "format": "json",
    }
    url = WIKIMEDIA_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"[wikimedia_fetch] API error: {e}", file=sys.stderr)
        return []

    pages = data.get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png", "image/jpg"):
            continue
        url_thumb = info.get("thumburl") or info.get("url")
        if not url_thumb:
            continue
        results.append({
            "title": page.get("title", ""),
            "url": url_thumb,
            "width": info.get("thumbwidth", 0),
            "height": info.get("thumbheight", 0),
        })
    return results[:count]


def download_image(url: str, dest: str) -> bool:
    """Download image to dest path."""
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        if len(data) < 5000:
            print(f"[wikimedia_fetch] Image too small ({len(data)} bytes), skipping", file=sys.stderr)
            return False
        with open(dest, "wb") as f:
            f.write(data)
        print(f"[wikimedia_fetch] ✅ Saved {dest} ({len(data)//1024}KB)")
        return True
    except Exception as e:
        print(f"[wikimedia_fetch] Download error: {e}", file=sys.stderr)
        return False


def fetch_scene_image(query: str, dest: str, count: int = 5) -> bool:
    """Fetch best image for a scene query. Returns True if successful."""
    print(f"[wikimedia_fetch] Searching: '{query}'")
    results = search_wikimedia(query, count)
    if not results:
        print(f"[wikimedia_fetch] No results for '{query}'", file=sys.stderr)
        return False
    # Try each result until one downloads successfully
    for r in results:
        print(f"[wikimedia_fetch] Trying: {r['title']}")
        if download_image(r["url"], dest):
            return True
    print(f"[wikimedia_fetch] All downloads failed for '{query}'", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(description="Fetch historical images from Wikimedia Commons")
    parser.add_argument("--query", required=True, help="Search query (e.g. 'Battle of Thermopylae')")
    parser.add_argument("--out", required=True, help="Output file path (e.g. images/scene_01.jpg)")
    parser.add_argument("--count", type=int, default=5, help="Number of results to try (default 5)")
    args = parser.parse_args()

    success = fetch_scene_image(args.query, args.out, args.count)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
