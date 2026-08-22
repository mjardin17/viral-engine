#!/usr/bin/env python3
"""Generate Whatnot bulk import CSV from Supabase products."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Proper load from repo root
load_dotenv(Path(__file__).parent / ".env")

from lib.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Fetch all products
response = supabase.table("products").select("*").eq("status", "active").execute()
products = response.data or []

print(f"[*] Fetched {len(products)} active products")

# Build Whatnot CSV
rows = [["Title", "Description", "Price", "Quantity", "Category", "Condition", "Shipping"]]

for p in products:
    title = (p.get("title") or "Item")[:100]
    description = (p.get("description") or "")[:500]
    price = float(p.get("price") or 0) or 29.99
    quantity = int(p.get("quantity") or 1)

    # Smart category mapping
    title_lower = title.lower()
    if "card" in title_lower or "trading" in title_lower or "pokemon" in title_lower:
        category = "Trading Card Games"
    elif "action figure" in title_lower or "transformer" in title_lower or "figure" in title_lower:
        category = "Action Figures"
    elif "hot wheel" in title_lower or "die cast" in title_lower or "car" in title_lower:
        category = "Toy Vehicles"
    elif "sneaker" in title_lower or "shoe" in title_lower:
        category = "Shoes & Sneakers"
    elif "cosmetic" in title_lower or "beauty" in title_lower:
        category = "Beauty & Personal Care"
    else:
        category = "Collectibles"

    condition = "Like New"
    shipping = "USPS"

    rows.append([title, description, f"{price:.2f}", str(quantity), category, condition, shipping])

# Write as CSV with proper quoting
csv_path = Path(__file__).parent / "whatnot_import.csv"
with open(csv_path, "w", encoding="utf-8") as f:
    for row in rows:
        quoted = [f'"{cell}"' if "," in cell or '"' in cell else cell for cell in row]
        f.write(",".join(quoted) + "\n")

print(f"[OK] {csv_path} generated with {len(rows)-1} items")
print(f"[OK] Ready for Whatnot Seller Hub > Inventory > Import from CSV")
