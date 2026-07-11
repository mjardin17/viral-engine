"""
merch_empire/scanner.py — Empire OS Merch Trend Scanner
Scans Redbubble, Merch by Amazon, Etsy, Google Trends for what's selling RIGHT NOW.
Outputs: merch_empire/TREND_BOARD.json — ranked list of winning design niches.

Usage:
    python merch_empire/scanner.py
    python merch_empire/scanner.py --top 20
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

MERCH_DIR   = Path(__file__).parent
TREND_BOARD = MERCH_DIR / "TREND_BOARD.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Redbubble trending search terms to probe
REDBUBBLE_PROBES = [
    "trending", "vintage", "aesthetic", "funny", "cat", "anime",
    "skull", "nature", "space", "retro", "gaming", "motivational",
    "mythology", "warriors", "dragon", "wolf", "eagle", "lion",
    "minimalist", "abstract", "floral", "sunset", "mountains",
]

# Amazon Merch bestseller categories
MBA_CATEGORIES = [
    ("T-Shirts Novelty",  "https://www.amazon.com/Best-Sellers-Clothing-Novelty-T-Shirts/zgbs/fashion/9056991011"),
    ("Hoodies",           "https://www.amazon.com/Best-Sellers-Clothing-Fashion-Hoodies-Sweatshirts/zgbs/fashion/1046088"),
    ("PopSockets",        "https://www.amazon.com/Best-Sellers-Electronics-PopSockets/zgbs/electronics/2407749011"),
]

# Etsy trending searches
ETSY_SEARCHES = [
    "https://www.etsy.com/search?q=trending+tshirt&ref=pagination",
    "https://www.etsy.com/search?q=funny+mug&ref=pagination",
    "https://www.etsy.com/search?q=vintage+hat&ref=pagination",
]


def scrape_redbubble_trending(probe: str) -> list[dict]:
    """Get trending design tags from a Redbubble search."""
    url  = f"https://www.redbubble.com/shop/?query={requests.utils.quote(probe)}&ref=search_box"
    tags: list[dict] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return tags
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract design titles / tags from results
        items = soup.select("span[class*='SearchResultsCard']")[:10]
        for item in items:
            text = item.get_text(strip=True)
            if text:
                tags.append({"source": "redbubble", "term": probe, "design": text[:60]})
    except Exception:
        pass
    return tags


def scrape_mba_category(name: str, url: str) -> list[dict]:
    """Scrape top designs from Amazon Merch bestseller page."""
    designs: list[dict] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return designs
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("div.zg-grid-general-faceout, li.zg-item-immersion")[:20]
        for item in items:
            title_el = item.select_one("div.p13n-sc-truncate-desktop-type2, a.a-link-normal span")
            title = title_el.get_text(strip=True) if title_el else ""
            if title:
                designs.append({"source": "amazon_merch", "category": name, "design": title[:80]})
    except Exception:
        pass
    return designs


def scrape_google_trends() -> list[dict]:
    """Pull daily trending searches from Google Trends RSS."""
    trends: list[dict] = []
    try:
        url  = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "xml")
        for item in soup.select("item")[:30]:
            title = item.find("title")
            if title:
                trends.append({"source": "google_trends", "term": title.get_text(strip=True)})
    except Exception:
        pass
    return trends


def cluster_and_score(raw: list[dict]) -> list[dict[str, Any]]:
    """Cluster raw signals into design niches with scores."""
    counts: dict[str, int]   = {}
    sources: dict[str, set]  = {}
    examples: dict[str, list] = {}

    for item in raw:
        key = item.get("term") or item.get("design") or item.get("category") or "unknown"
        # Normalize to key themes
        key = key.lower().strip()[:40]
        counts[key]   = counts.get(key, 0) + 1
        sources[key]  = sources.get(key, set()) | {item["source"]}
        if key not in examples:
            examples[key] = []
        if len(examples[key]) < 3:
            examples[key].append(item.get("design", item.get("term", key)))

    niches: list[dict[str, Any]] = []
    for key, count in sorted(counts.items(), key=lambda x: -x[1]):
        source_count = len(sources[key])
        score = count * 3 + source_count * 10
        niches.append({
            "niche":        key,
            "signal_count": count,
            "sources":      list(sources[key]),
            "score":        score,
            "examples":     examples[key],
        })

    return niches


def run_scan(top_n: int = 20) -> list[dict]:
    print("\n[MERCH SCANNER] Starting trend scan...")
    raw: list[dict] = []

    # Redbubble probes
    print("  Scanning Redbubble...")
    for probe in REDBUBBLE_PROBES[:8]:
        raw += scrape_redbubble_trending(probe)
        time.sleep(1)

    # Amazon Merch
    print("  Scanning Merch by Amazon...")
    for name, url in MBA_CATEGORIES:
        raw += scrape_mba_category(name, url)
        time.sleep(2)

    # Google Trends
    print("  Scanning Google Trends...")
    raw += scrape_google_trends()

    # Score and rank
    niches = cluster_and_score(raw)[:top_n]

    output = {
        "scanned_at":  datetime.utcnow().isoformat() + "Z",
        "total_signals": len(raw),
        "niches": niches,
    }
    TREND_BOARD.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"\n[MERCH SCANNER] Done — {len(raw)} signals → {len(niches)} niches")
    print(f"  Saved: merch_empire/TREND_BOARD.json\n")
    for i, n in enumerate(niches[:10], 1):
        print(f"  #{i:2d}  {n['niche']:30s}  score={n['score']:4d}  sources={n['sources']}")

    return niches


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=20)
    args = p.parse_args()
    run_scan(args.top)
