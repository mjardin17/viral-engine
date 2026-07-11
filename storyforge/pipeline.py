"""
storyforge/pipeline.py — Empire OS Full Book + Merch Pipeline
One command: scan → pick niche → generate book → format EPUB+PDF → generate merch assets → queue for upload.

Usage:
    python storyforge/pipeline.py                  # full auto run
    python storyforge/pipeline.py --niche "Military History" --title "Lost Battles of WWII"
    python storyforge/pipeline.py --scan-only      # just scan niches
    python storyforge/pipeline.py --books 3        # auto-generate 3 books back to back
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent to path so imports work when run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from storyforge.scanner   import run_scan
from storyforge.generator import run_generator, auto_pick_niche, call_gemini
from storyforge.formatter import format_book
from storyforge.merch     import generate_merch_assets

STORYFORGE  = Path(__file__).parent
BOOKS_DIR   = STORYFORGE / "books"
NICHE_BOARD = STORYFORGE / "NICHE_BOARD.json"
QUEUE_FILE  = STORYFORGE / "UPLOAD_QUEUE.json"


def load_queue() -> dict:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return {"books": [], "merch": []}


def save_queue(q: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(q, indent=2), encoding="utf-8")


def queue_book_for_upload(manifest_path: Path) -> None:
    """Add a formatted book to the upload queue."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    q = load_queue()

    already = [b["slug"] for b in q["books"]]
    if manifest["slug"] not in already:
        q["books"].append({
            "slug":      manifest["slug"],
            "title":     manifest["title"],
            "epub":      manifest.get("epub", ""),
            "pdf":       manifest.get("pdf", ""),
            "keywords":  manifest.get("keywords", ""),
            "description": manifest.get("description", ""),
            "status":    "pending_upload",
            "queued_at": datetime.utcnow().isoformat() + "Z",
        })

    if manifest.get("merch_dir"):
        q["merch"].append({
            "slug":      manifest["slug"],
            "title":     manifest["title"],
            "merch_dir": manifest["merch_dir"],
            "status":    "pending_upload",
            "queued_at": datetime.utcnow().isoformat() + "Z",
        })

    save_queue(q)
    print(f"  [PIPELINE] Queued for upload: {manifest['title']}")


def run_full_pipeline(niche: str = "", title: str = "", books: int = 1) -> None:
    print("\n" + "="*60)
    print("  EMPIRE OS — STORYFORGE PIPELINE")
    print("="*60)

    # Step 1: Scan if no niche board or explicitly requested
    if not NICHE_BOARD.exists():
        print("\n[1/5] Scanning niches...")
        run_scan()
    else:
        print("\n[1/5] Niche board exists — skipping scan (run scanner.py to refresh)")

    for book_num in range(books):
        if books > 1:
            print(f"\n{'='*60}")
            print(f"  BOOK {book_num + 1} of {books}")
            print(f"{'='*60}")

        # Step 2: Pick niche + title
        print("\n[2/5] Selecting niche and title...")
        if not niche:
            _niche, _title = auto_pick_niche()
        else:
            _niche, _title = niche, title

        print(f"  Niche: {_niche}")
        print(f"  Title: {_title}")

        # Step 3: Generate book
        print("\n[3/5] Generating book content + cover...")
        book_dir = run_generator(_niche, _title)
        manifest_path = book_dir / "manifest.json"

        # Step 4: Format EPUB + PDF
        print("\n[4/5] Formatting EPUB + PDF...")
        try:
            format_book(book_dir.name)
        except Exception as e:
            print(f"  [PIPELINE] Format error: {e}")

        # Step 5: Generate merch assets
        print("\n[5/5] Generating merch assets...")
        try:
            generate_merch_assets(book_dir.name)
        except Exception as e:
            print(f"  [PIPELINE] Merch error: {e}")

        # Queue for upload
        queue_book_for_upload(manifest_path)

        if book_num < books - 1:
            print("\n  Cooling down 10s before next book...")
            time.sleep(10)

    # Final summary
    q = load_queue()
    print("\n" + "="*60)
    print(f"  PIPELINE COMPLETE")
    print(f"  Books queued for upload: {len(q['books'])}")
    print(f"  Merch packs queued:      {len(q['merch'])}")
    print(f"  Queue file: storyforge/UPLOAD_QUEUE.json")
    print("="*60)
    print("\nNext step: run  python storyforge/uploader.py  to push to KDP + Draft2Digital + Redbubble")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Empire OS Book + Merch Pipeline")
    p.add_argument("--niche",      default="", help="Book niche (leave blank for auto)")
    p.add_argument("--title",      default="", help="Book title (leave blank for auto)")
    p.add_argument("--books",      type=int, default=1, help="Number of books to generate")
    p.add_argument("--scan-only",  action="store_true", help="Only run niche scanner")
    args = p.parse_args()

    if args.scan_only:
        run_scan()
    else:
        run_full_pipeline(args.niche, args.title, args.books)
