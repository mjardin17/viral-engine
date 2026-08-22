#!/usr/bin/env python3
"""Fetch ALL inventory items from eBay (not just the first 69)"""

import os
from dotenv import load_dotenv
from lib.ebay_listing import EbayListingClient

load_dotenv()
refresh_token = os.getenv("EBAY_REFRESH_TOKEN")
client = EbayListingClient(access_token=refresh_token, sandbox=False)

# Fetch ALL inventory items (paginated)
all_items = []
limit = 100
offset = 0

while True:
    result = client.client.get_inventory_items(
        limit=limit,
        offset=offset
    )
    items = result.get("inventoryItems", [])
    if not items:
        break
    all_items.extend(items)
    offset += limit
    print(f"Fetched {len(all_items)} items...")
    if len(items) < limit:
        break

print(f"\nTotal inventory items via Inventory API: {len(all_items)}")
if all_items:
    print(f"First item: {all_items[0].get('sku')}")
