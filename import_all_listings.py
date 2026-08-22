#!/usr/bin/env python3
"""Fetch all eBay listings via Trading API and import to Supabase"""

import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from lib.supabase_client import get_supabase_client

load_dotenv()

user_token = os.getenv("EBAY_AUTH_TOKEN")
base_url = "https://api.ebay.com/ws/api.dll"

headers = {
    "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
    "X-EBAY-API-REQUEST-ENCODING": "XML",
    "X-EBAY-API-RESPONSE-ENCODING": "XML",
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
    "X-EBAY-API-SITEID": "0",
    "X-EBAY-API-IAF-TOKEN": user_token,
    "Content-Type": "text/xml",
}

# Use service_role key for full access
from supabase import create_client
url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, service_key)

all_items = []
page = 1

print("Fetching ALL listings from eBay...")

while True:
    body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{user_token}</eBayAuthToken>
    </RequesterCredentials>
    <ActiveList>
        <Pagination>
            <EntriesPerPage>100</EntriesPerPage>
            <PageNumber>{page}</PageNumber>
        </Pagination>
    </ActiveList>
</GetMyeBaySellingRequest>"""

    response = requests.post(base_url, data=body.encode(), headers=headers)

    if response.status_code != 200:
        print(f"ERROR {response.status_code}")
        break

    text = response.text
    if "<Ack>Failure</Ack>" in text:
        break

    # Parse XML
    try:
        root = ET.fromstring(text)
        # eBay namespace
        ns = {'ebay': 'urn:ebay:apis:eBLBaseComponents'}
        items = root.findall('.//ebay:Item', ns)

        if not items:
            break

        for item in items:
            item_id = item.findtext('{urn:ebay:apis:eBLBaseComponents}ItemID')
            title = item.findtext('{urn:ebay:apis:eBLBaseComponents}Title')
            current_price = item.findtext('.//{urn:ebay:apis:eBLBaseComponents}CurrentPrice')
            quantity = item.findtext('{urn:ebay:apis:eBLBaseComponents}Quantity')

            if item_id and title:
                all_items.append({
                    'sku': f"v1|{item_id}|0",
                    'title': title,
                    'price': float(current_price) if current_price else 0,
                    'quantity': int(quantity) if quantity else 1,
                    'ebay_listing_id': f"v1|{item_id}|0",
                    'status': 'active',
                    'source': 'ebay',
                })

        print(f"  Page {page}: {len(items)} items, total so far: {len(all_items)}")

        if len(items) < 100:
            break

        page += 1

    except Exception as e:
        print(f"Error parsing XML: {e}")
        break

print(f"\n✓ Total items to import: {len(all_items)}")

# Import to Supabase (upsert = update if exists, insert if new)
if all_items:
    print(f"Importing to Supabase...")
    try:
        # Break into chunks to avoid huge single request
        chunk_size = 50
        for i in range(0, len(all_items), chunk_size):
            chunk = all_items[i:i+chunk_size]
            response = supabase.table("products").upsert(chunk).execute()
            print(f"  Chunk {i//chunk_size + 1}: {len(response.data)} items")
        print(f"✓ Upserted all {len(all_items)} items")
    except Exception as e:
        print(f"Error importing: {e}")

print("\nNow run: python scripts/inventory_sync.py")
