#!/usr/bin/env python3
"""
bosslister_commercial_feeder.py — Wire BossListers inventory into commercial rendering.

Fetches product listings from BossListers Supabase (public.products table),
generates commercial render missions, and queues them in MISSION_BOARD.json.

Usage:
    python tools/bosslister_commercial_feeder.py --test              # Test with one product
    python tools/bosslister_commercial_feeder.py --all               # Queue all products
    python tools/bosslister_commercial_feeder.py --sku SKU123        # Queue one by SKU
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase-py not installed. Install with: pip install supabase")
    sys.exit(1)

# Add lib/ to path so we can import commercial_generator
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.commercial_generator import create_commercial_mission

# ─── Config ───────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://irslzufsqjveyibkfjtz.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
MISSION_BOARD_PATH = BASE_DIR / "MISSION_BOARD.json"

if not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_SERVICE_ROLE_KEY not set in environment")
    print("  Add to .env: SUPABASE_SERVICE_ROLE_KEY from BossListers .env.local")
    sys.exit(1)


def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def fetch_products(sku=None, limit=None):
    """Fetch products from BossListers Supabase."""
    supabase = get_supabase_client()

    query = supabase.table("products").select("id, sku, title, description, price, image_url, quantity, published")

    if sku:
        query = query.eq("sku", sku)

    if limit:
        query = query.limit(limit)

    try:
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"ERROR: Failed to fetch products from Supabase: {e}")
        sys.exit(1)


def generate_mission_id(product_sku):
    """Generate a unique mission ID for a product."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"commercial-{product_sku}-{timestamp}"


def load_mission_board():
    """Load the current mission board."""
    if not MISSION_BOARD_PATH.exists():
        print(f"ERROR: {MISSION_BOARD_PATH} not found")
        sys.exit(1)

    with MISSION_BOARD_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_mission_board(board):
    """Save mission board with updated timestamp."""
    board["updated_at"] = datetime.now().isoformat()
    with MISSION_BOARD_PATH.open("w", encoding="utf-8") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✓ Saved mission board: {MISSION_BOARD_PATH}")


def queue_commercial(product, dry_run=False):
    """Create a commercial mission for a product and add to board."""

    # Extract product fields
    sku = product.get("sku", product.get("id", "unknown"))
    name = product.get("title", "Unknown Product")
    description = product.get("description", "High-quality product")
    price = product.get("price", 0)

    # Collect images: BossListers stores a single image_url (relative path)
    image_url = product.get("image_url")
    if not image_url:
        print(f"⚠ SKIP {sku}: No image found")
        return None

    # Convert relative path to absolute URL if needed
    if image_url.startswith("/"):
        # For now, use a placeholder domain — in production, use BossListers domain
        # This will be resolved to real URLs when rendering
        image_url = f"https://bosslister.app{image_url}"

    images = [image_url]

    # Generate mission
    mission_id = generate_mission_id(sku)
    mission = create_commercial_mission(name, description, price, images, mission_id)

    if dry_run:
        print(f"\n📋 DRY-RUN: Would queue commercial for '{name}'")
        print(f"   Mission ID: {mission_id}")
        print(f"   SKU: {sku}")
        print(f"   Price: ${price}")
        print(f"   Images: {len(images)} found")
        print(f"   Scenes: {len(mission['render_script']['scenes'])}")
        return mission

    # Add to board
    board = load_mission_board()

    # Check if already queued
    existing = [m for m in board["missions"] if m.get("product", {}).get("sku") == sku]
    if existing:
        print(f"⚠ {sku}: Already queued as {existing[0]['id']}")
        return None

    board["missions"].append(mission)
    save_mission_board(board)

    print(f"✓ Queued commercial for '{name}' (ID: {mission_id})")
    return mission


def main():
    parser = argparse.ArgumentParser(description="Queue BossListers products for commercial rendering")
    parser.add_argument("--test", action="store_true", help="Test mode: show one product without saving")
    parser.add_argument("--all", action="store_true", help="Queue all products")
    parser.add_argument("--sku", help="Queue a specific product by SKU")
    parser.add_argument("--limit", type=int, help="Limit number of products to queue")

    args = parser.parse_args()

    # Determine mode
    if args.test:
        products = fetch_products(limit=1)
        if not products:
            print("No products found in Supabase")
            sys.exit(1)

        product = products[0]
        print(f"\n🧪 Test Mode: Fetched '{product.get('title', 'Unknown')}'")
        queue_commercial(product, dry_run=True)
        print("\n✓ This is a dry run. No missions were saved.")

    elif args.sku:
        products = fetch_products(sku=args.sku)
        if not products:
            print(f"No product found with SKU: {args.sku}")
            sys.exit(1)

        queue_commercial(products[0])

    elif args.all:
        products = fetch_products(limit=args.limit)
        if not products:
            print("No products found in Supabase")
            sys.exit(1)

        queued = 0
        for product in products:
            result = queue_commercial(product)
            if result:
                queued += 1

        print(f"\n✓ Queued {queued}/{len(products)} products")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
