#!/usr/bin/env python3
"""
Standalone runner for the Book Factory autonomous daemon.

Usage:
    python run_book_factory.py          # One cycle, dry-run (safe default)
    python run_book_factory.py --live   # One cycle, LIVE publishing (requires approval)

Designed to be called by a scheduled task (daily, hourly, etc.) or manually.
All state is persisted to books/factory_state.db for resumability.

Credentials expected in .env:
    ANTHROPIC_API_KEY — Claude API for real manuscript generation (Patterson formula)
    KDP_EMAIL, KDP_PASSWORD — Amazon KDP
    D2D_API_KEY — Draft2Digital
    PAYHIP_API_KEY — Payhip
    ETSY_ACCESS_TOKEN, ETSY_SHOP_ID, ETSY_API_KEY — Etsy
    (and others per storyforge2/books/factory.py::_load_credentials)
"""

import sys
import os
from pathlib import Path

# Add repo root to path so we can import storyforge2
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Load .env if it exists
from dotenv import load_dotenv
load_dotenv()

from storyforge2.books.factory import BookFactory


def main():
    """Run one factory cycle."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Book Factory daemon runner — generates and publishes books autonomously"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Publish books for real (default: dry-run only)"
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path("books"),
        help="Directory for factory state (default: books/)"
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"BOOK FACTORY DAEMON")
    print(f"Mode: {'LIVE PUBLISHING' if not args.live else 'DRY-RUN (SAFE)'}")
    print(f"State dir: {args.state_dir}")
    print(f"{'='*70}\n")

    try:
        factory = BookFactory(work_base=args.state_dir)

        # Run one full cycle
        cycle = factory.run_cycle(dry_run=not args.live)

        if cycle:
            print(f"\n{'='*70}")
            print(f"CYCLE COMPLETE: {cycle.cycle_id}")
            print(f"Title: {cycle.opportunity.title}")
            print(f"Status: {cycle.status}")
            if cycle.metadata:
                print(f"ISBN: {cycle.metadata.isbn}")
            if cycle.error:
                print(f"Error: {cycle.error}")
            print(f"{'='*70}\n")
            return 0
        else:
            print("\n[INFO] No opportunity due yet. Skipping cycle.\n")
            return 0

    except Exception as e:
        print(f"\n[ERROR] Factory cycle failed: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
