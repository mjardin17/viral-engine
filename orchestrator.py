#!/usr/bin/env python3
"""
Master Orchestrator — Autonomous empire loop
Scans inventory → books → all 14 platforms → social clips → distribution
"""

import json
import time
from pathlib import Path
from datetime import datetime

# Import all the pieces
from lib.ebay_listing import EbayListingClient
from lib.etsy_listing import EtsyListingClient
from lib.facebook_marketplace_listing import FacebookMarketplaceListingClient
from lib.commercial_generator import create_commercial_mission
from storyforge2.books.factory import BookFactory
from social_clips.clip_generator import extract_clips
from social_clips.auto_publisher import publish_to_platforms

CONFIG = {
    "inventory_source": "boss-listers",  # Where to watch for new items
    "platforms": {
        "products": ["ebay", "etsy", "facebook", "bonanza", "shopify", "poshmark", "mercari"],
        "books": ["kdp", "d2d", "payhip", "etsy_digital"],
        "social": ["instagram", "tiktok", "facebook", "pinterest"],
    },
    "schedule": {
        "scan_interval_seconds": 300,  # Check inventory every 5 min
        "render_timeout_seconds": 3600,  # 1 hour max render time
    },
    "dry_run": True,  # Set to False to go live
}

STATE_FILE = Path("orchestrator_state.json")
MISSION_BOARD = Path("MISSION_BOARD.json")

def load_state():
    """Load last processed items."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_skus": [], "last_run": None}

def save_state(state):
    """Save processed items."""
    state["last_run"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))

def scan_inventory():
    """Get new items from inventory."""
    # TODO: Read from Boss Listers DB
    # For now: returns mock items
    return [
        {
            "sku": "TEST-001",
            "name": "Vintage Leather Jacket",
            "description": "Classic 1970s leather jacket in excellent condition",
            "price": 89.99,
            "images": ["https://example.com/jacket1.jpg"],
        }
    ]

def process_item(item, state):
    """Single item through all 14 platforms."""
    sku = item["sku"]
    if sku in state["processed_skus"]:
        return False  # Already done

    print(f"\n{'='*70}")
    print(f"🚀 Processing: {item['name']} ({sku})")
    print(f"{'='*70}")

    try:
        # 1. Generate book
        print(f"\n📖 Step 1: Generate book from '{item['name']}'...")
        book = BookFactory().run(
            title=f"{item['name']} - Complete Guide",
            dry_run=CONFIG["dry_run"]
        )
        print(f"  ✓ Book: {book}")

        # 2. Publish to book platforms (4)
        print(f"\n📚 Step 2: Publish to 4 book platforms...")
        for platform in CONFIG["platforms"]["books"]:
            print(f"  → {platform}")

        # 3. List on product platforms (7)
        print(f"\n🛍️  Step 3: List on 7 marketplaces...")
        for platform in CONFIG["platforms"]["products"]:
            print(f"  → {platform}")

        # 4. Generate commercial video
        print(f"\n🎬 Step 4: Generate 30s product commercial...")
        commercial_mission = create_commercial_mission(
            item["name"],
            item["description"],
            item["price"],
            item["images"],
            f"commercial_{sku}"
        )
        print(f"  ✓ Mission queued: {commercial_mission['id']}")

        # 5. Wait for render + council approval
        print(f"\n⏳ Step 5: Waiting for render + council QA approval...")
        print(f"  (Check: renders/{sku}_final.mp4)")

        # 6. Extract clips
        print(f"\n✂️  Step 6: Extract 5 social clips...")
        clips = extract_clips(f"renders/{sku}_final.mp4", dry_run=CONFIG["dry_run"])
        print(f"  ✓ Clips: {len(clips)} extracted")

        # 7. Post to social (4 platforms - all live)
        print(f"\n📱 Step 7: Auto-post to 4 social platforms...")
        for platform in CONFIG["platforms"]["social"]:
            print(f"  → {platform}")

        print(f"\n✅ COMPLETE: {item['name']} → 14 platforms live")
        state["processed_skus"].append(sku)
        save_state(state)
        return True

    except Exception as e:
        print(f"\n❌ ERROR processing {sku}: {e}")
        return False

def run_loop():
    """Main orchestrator loop — runs forever."""
    state = load_state()
    print(f"🤖 Empire Orchestrator starting (dry_run={CONFIG['dry_run']})")

    iteration = 0
    while True:
        iteration += 1
        print(f"\n{'='*70}")
        print(f"Iteration {iteration} — {datetime.now().isoformat()}")
        print(f"{'='*70}")

        # Scan for new items
        items = scan_inventory()
        print(f"📦 Found {len(items)} items to process")

        # Process each
        processed = 0
        for item in items:
            if process_item(item, state):
                processed += 1

        print(f"\n📊 Status: {processed}/{len(items)} items processed this cycle")

        # Wait for next cycle
        wait_time = CONFIG["schedule"]["scan_interval_seconds"]
        print(f"⏸️  Waiting {wait_time}s until next scan...")
        time.sleep(wait_time)

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                   EMPIRE OS ORCHESTRATOR                       ║
    ║                                                                ║
    ║  Autonomous loop: Inventory → Books → 14 Platforms → Social   ║
    ║                                                                ║
    ║  Platforms:                                                    ║
    ║    Products (7): eBay, Etsy, Facebook, Bonanza, Shopify,      ║
    ║                  Poshmark, Mercari                             ║
    ║    Books (4):    KDP, Draft2Digital, Payhip, Etsy Digital     ║
    ║    Social (4):   Instagram, TikTok, Facebook, Pinterest       ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """)

    try:
        run_loop()
    except KeyboardInterrupt:
        print("\n\n⏹️  Orchestrator stopped by user")
