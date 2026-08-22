#!/usr/bin/env python3
from dotenv import load_dotenv
import os
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

result = supabase.table("products").select("sku, title, status, ebay_listing_id").limit(5).execute()
print(f"Total fetched: {len(result.data)}")
for p in result.data:
    print(f"  {p.get('sku')} - status={p.get('status', 'NULL')} - ebay_listing_id={p.get('ebay_listing_id', 'NULL')}")
