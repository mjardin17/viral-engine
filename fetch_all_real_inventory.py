#!/usr/bin/env python3
"""Fetch ALL inventory items from eBay and sync to Supabase"""

import os
import requests
from dotenv import load_dotenv
from lib.supabase_client import get_supabase_client
from lib.ebay_oauth import exchange_refresh_token

load_dotenv()

# Exchange refresh token for access token
refresh_token = os.getenv("EBAY_REFRESH_TOKEN")
client_id = os.getenv("EBAY_CLIENT_ID")
client_secret = os.getenv("EBAY_CLIENT_SECRET")

access_token = exchange_refresh_token(refresh_token, client_id, client_secret)
print(f"✓ Got access token")

base_url = "https://api.ebay.com/sell/inventory/v1"

# Fetch using the access token
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
}

all_items = []
limit = 100
offset = 0

print("Fetching ALL inventory from eBay...")

while True:
    url = f"{base_url}/inventory_item?limit={limit}&offset={offset}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR {response.status_code}: {response.text}")
        break

    data = response.json()
    items = data.get("inventoryItems", [])

    if not items:
        break

    all_items.extend(items)
    print(f"  Fetched {len(all_items)} items so far...")

    if len(items) < limit:
        break

    offset += limit

print(f"\n✓ Total inventory items: {len(all_items)}")

# Get SKU count
skus = [item.get("sku") for item in all_items if item.get("sku")]
print(f"✓ Items with SKUs: {len(skus)}")
print(f"\nFirst 5 SKUs:")
for sku in skus[:5]:
    print(f"  {sku}")
