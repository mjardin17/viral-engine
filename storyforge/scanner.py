"""
storyforge/scanner.py — Empire OS Niche Scanner
Scans Amazon bestsellers + Google Trends to find winning book/merch niches.
Outputs: storyforge/NICHE_BOARD.json

Usage:
    python storyforge/scanner.py
    python storyforge/scanner.py --top 10
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

REPO        = Path(__file__).parent.parent
NICHE_BOARD = Path(__file__).parent / "NICHE_BOARD.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Amazon Kindle bestseller categories to scan
AMAZON_CATEGORIES: list[tuple[str, str]] = [
    ("History",          "https://www.amazon.com/Best-Sellers-Kindle-Store-History/zgbs/digital-text/6256978011"),
    ("Mythology",        "https://www.amazon.com/Best-Sellers-Kindle-Store-Mythology/zgbs/digital-text/6256973011"),
    ("Military History", "https://www.amazon.com/Best-Sellers-Kindle-Store-Military-History/zgbs/digital-text/6256969011"),
    ("Action Adventure", "https://www.amazon.com/Best-Sellers-Kindle-Store-Action-Adventure/zgbs/digital-text/6256916011"),
    ("Short Stories",    "https://www.amazon.com/Best-Sellers-Kindle-Store-Short-Stories/zgbs/digital-text/6256913011"),
    ("Epic Fantasy",     "https://www.amazon.com/Best-Sellers-Kindle-Store-Epic-Fantasy/zgbs/digital-text/6256919011"),
    ("Self Help",        "https://www.amazon.com/Best-Sellers-Books-Self-Help/zgbs/books/4906"),
    ("Coloring Books",   "https://www.amazon.com/Best-Sellers-Books-Coloring-Books/zgbs/books/4106"),
]


def scrape_amazon_category(name: str, url: str) -> list[dict[str, Any]]:
    """Scrape top 20 books from an Amazon bestseller category page."""
    books: list[dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [SCANNER] {name}: HTTP {resp.status_code} — skipping")
            return books

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("div.zg-grid-general-faceout, li.zg-item-immersion")[:20]

        for item in items:
            title_el = item.select_one("div.p13n-sc-truncate-desktop-type2, span.zg-text-center-align")
            price_el = item.select_one("span.p13n-sc-price, span._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y")
            rank_el  = item.select_one("span.zg-badge-text")

            title = title_el.get_text(strip=True) if title_el else "Unknown"
            price = price_el.get_text(strip=True) if price_el else "$0.00"
            rank  = rank_el.get_text(strip=True) if rank_el else "#?"

            books.append({
                "category": name,
                "title":    title[:80],
                "price":    price,
                "rank":     rank,
            })

        print(f"  [SCANNER] {name}: found {len(books)} titles")
    except Exception as e:
        print(f"  [SCANNER] {name}: error — {e}")

    return books


def score_niche(category: str, books: list[dict]) -> dict[str, Any]:
    """Score a niche based on count, avg price, and Empire OS channel alignment."""
    if not books:
        return {}

    # Extract prices
    prices: list[float] = []
    for b in books:
        m = re.search(r"[\d.]+", b.get("price", "0"))
        if m:
            prices.append(float(m.group()))

    avg_price    = sum(prices) / len(prices) if prices else 0.0
    count        = len(books)

    # Alignment bonus: our channels are history, mythology, military, anime/mech, kids mythology
    alignment_keywords = ["history", "myth", "military", "war", "ancient", "legend", "fantasy", "battle", "empire"]
    alignment = any(kw in category.lower() for kw in alignment_keywords)

    score = (count * 2) + (avg_price * 3) + (10 if alignment else 0)

    return {
        "category":    category,
        "book_count":  count,
        "avg_price":   round(avg_price, 2),
        "alignment":   alignment,
        "score":       round(score, 1),
        "sample_titles": [b["title"] for b in books[:3]],
    }


def run_scan(top_n: int = 10) -> list[dict[str, Any]]:
    print("\n[SCANNER] Starting niche scan...")
    all_results: list[dict[str, Any]] = []

    for name, url in AMAZON_CATEGORIES:
        books = scrape_amazon_category(name, url)
        scored = score_niche(name, books)
        if scored:
            all_results.append(scored)
        time.sleep(2)  # be polite

    # Sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    top = all_results[:top_n]

    output = {
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "niches": top,
    }
    NICHE_BOARD.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"\n[SCANNER] Done. Top {top_n} niches saved to storyforge/NICHE_BOARD.json")
    for i, n in enumerate(top, 1):
        print(f"  #{i:2d}  {n['category']:25s}  score={n['score']:5.1f}  avg_price=${n['avg_price']:.2f}")

    return top


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args()
    run_scan(args.top)
