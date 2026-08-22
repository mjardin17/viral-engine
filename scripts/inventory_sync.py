#!/usr/bin/env python3
"""
Inventory sync: Auto-publish to Poshmark & Mercari via browser automation.
Whatnot API coming soon.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.supabase_client import get_supabase_client
from lib.undetected_connectors import PoshmarkConnector, MercariConnector

DRY_RUN = True  # Set to False to actually publish


def publish_to_poshmark(products: list) -> int:
    """Auto-publish listings to Poshmark."""
    success = 0
    try:
        connector = PoshmarkConnector()
        if not connector.authenticate():
            print("[!] Poshmark: Authentication failed. Check POSHMARK_USERNAME/PASSWORD")
            return 0

        print(f"\nPublishing {len(products)} items to Poshmark...")
        for product in products[:5]:  # Limit to 5 per run to avoid rate limits
            title = product.get("title", "Item")
            description = product.get("description", "")
            price = float(product.get("price", 0)) or 29.99
            images = [product["image_url"]] if product.get("image_url") else []

            if not DRY_RUN:
                result = connector.create_listing(title, description, price, images)
                if result:
                    success += 1
                    print(f"  [OK] {title}")
            else:
                print(f"  [DRY RUN] {title} -> ${price}")

    except Exception as e:
        print(f"[ERROR] Poshmark error: {e}")

    return success


def publish_to_mercari(products: list) -> int:
    """Auto-publish listings to Mercari."""
    success = 0
    try:
        connector = MercariConnector()
        if not connector.authenticate():
            print("[!] Mercari: Authentication failed. Check MERCARI_EMAIL/PASSWORD")
            return 0

        print(f"\nPublishing {len(products)} items to Mercari...")
        for product in products[:5]:  # Limit to 5 per run
            title = product.get("title", "Item")
            description = product.get("description", "")
            price = float(product.get("price", 0)) or 29.99
            images = [product["image_url"]] if product.get("image_url") else []

            if not DRY_RUN:
                result = connector.create_listing(title, description, price, images)
                if result:
                    success += 1
                    print(f"  [OK] {title}")
            else:
                print(f"  [DRY RUN] {title} -> ${price}")

    except Exception as e:
        print(f"[ERROR] Mercari error: {e}")

    return success


def main():
    load_dotenv()
    supabase = get_supabase_client()

    print(f"Inventory Sync - {'DRY RUN' if DRY_RUN else 'LIVE MODE'}")
    print("=" * 60)

    # Get all active products
    response = supabase.table("products").select("*").eq("status", "active").execute()
    products = response.data or []

    print(f"\nFound {len(products)} active products (already live on eBay)")

    if not products:
        print("No products to sync.")
        return

    # Auto-publish to Poshmark & Mercari
    posh_success = publish_to_poshmark(products)
    merc_success = publish_to_mercari(products)

    print("\n" + "=" * 60)
    print(f"Poshmark: {posh_success} published")
    print(f"Mercari: {merc_success} published")
    print(f"Whatnot: Use CSV bulk import (see whatnot_import.csv)")
    print("[OK] Sync complete!")


if __name__ == "__main__":
    main()
