"""
merch_empire/pipeline.py — Empire OS Merch Pipeline Orchestrator
Full auto: scan trends → pick winners → design variations → format all platforms → queue for upload.

Usage:
    python merch_empire/pipeline.py                  # scan + design top 5 niches
    python merch_empire/pipeline.py --niches 10      # top 10
    python merch_empire/pipeline.py --scan-only      # just update trend board
    python merch_empire/pipeline.py --design-only    # design from existing trend board
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from merch_empire.scanner  import run_scan
from merch_empire.designer import auto_design

MERCH_DIR   = Path(__file__).parent
TREND_BOARD = MERCH_DIR / "TREND_BOARD.json"
UPLOAD_Q    = MERCH_DIR / "UPLOAD_QUEUE.json"


def load_queue() -> dict:
    if UPLOAD_Q.exists():
        return json.loads(UPLOAD_Q.read_text(encoding="utf-8"))
    return {"designs": []}


def save_queue(q: dict) -> None:
    UPLOAD_Q.write_text(json.dumps(q, indent=2), encoding="utf-8")


def queue_designs(design_dirs: list[Path]) -> None:
    q = load_queue()
    existing_slugs = {d["slug"] for d in q["designs"]}

    for d in design_dirs:
        manifest_path = d / "manifest.json"
        if not manifest_path.exists():
            continue
        m = json.loads(manifest_path.read_text())
        if m["slug"] in existing_slugs:
            continue

        q["designs"].append({
            "slug":        m["slug"],
            "niche":       m["niche"],
            "variants":    len(m.get("variants", [])),
            "design_dir":  str(d),
            "status":      "pending_upload",
            "platforms":   ["redbubble", "merch_by_amazon", "printful", "spring", "etsy"],
            "queued_at":   datetime.utcnow().isoformat() + "Z",
        })

    save_queue(q)


def run_pipeline(niches: int = 5, variants: int = 3, scan: bool = True, design: bool = True) -> None:
    print("\n" + "="*60)
    print("  EMPIRE OS — MERCH PIPELINE")
    print("  Scan → Design → Format → Queue")
    print("="*60)

    if scan:
        print("\n[1/3] Scanning trends...")
        run_scan(top_n=niches * 2)

    if design:
        print(f"\n[2/3] Designing top {niches} niches ({variants} variants each)...")
        design_dirs = auto_design(count=niches, variants=variants)
    else:
        # Load from existing manifests
        design_dirs = [
            d for d in (MERCH_DIR / "designs").iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        ]

    print("\n[3/3] Queuing for upload...")
    queue_designs(design_dirs)

    q = load_queue()
    print("\n" + "="*60)
    print(f"  MERCH PIPELINE COMPLETE")
    print(f"  Designs queued: {len(q['designs'])}")
    print(f"  Platforms:      Redbubble, MBA, Printful, Spring, Etsy")
    print(f"  Queue file:     merch_empire/UPLOAD_QUEUE.json")
    print("="*60)
    print("\nNext: run  python merch_empire/uploader.py  to push to all platforms")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Empire OS Merch Pipeline")
    p.add_argument("--niches",      type=int, default=5,  help="Number of top niches to design")
    p.add_argument("--variants",    type=int, default=3,  help="Style variants per niche")
    p.add_argument("--scan-only",   action="store_true")
    p.add_argument("--design-only", action="store_true")
    args = p.parse_args()

    run_pipeline(
        niches=args.niches,
        variants=args.variants,
        scan=not args.design_only,
        design=not args.scan_only,
    )
