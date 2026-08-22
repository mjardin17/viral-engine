#!/usr/bin/env python3
"""Fetch ALL of Josh's eBay items via Browse API (no keyword filters)"""

import requests
from dotenv import load_dotenv
import os

load_dotenv()

base_url = "https://api.ebay.com/buy/browse/v1"

# Browse API is public — try without auth
headers = {
    "Content-Type": "application/json",
}

all_items = []
limit = 100
offset = 0

print("Fetching ALL items for seller mjardin17 via Browse API...")

while True:
    # Use seller filter with pagination, NO keyword constraint
    url = f"{base_url}/item_summary/search?filter=sellers:{{mjardin17}}&limit={limit}&offset={offset}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR {response.status_code}: {response.text[:200]}")
        break

    data = response.json()
    items = data.get("itemSummaries", [])

    if not items:
        break

    all_items.extend(items)
    total = data.get("total", len(all_items))
    print(f"  Fetched {len(all_items)}/{total} items...")

    if len(items) < limit:
        break

    offset += limit

print(f"\n✓ Total items found: {len(all_items)}")

if all_items:
    print(f"\nFirst 5 items:")
    for item in all_items[:5]:
        print(f"  {item.get('title')} - ${item.get('price', {}).get('value')} - ID: {item.get('itemId')}")
