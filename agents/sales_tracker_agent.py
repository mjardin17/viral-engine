#!/usr/bin/env python3
"""
Sales Tracker Agent: Monitors platforms for sold items and updates Boss Listers inventory.
Pulls sales data from Poshmark, Mercari, Etsy, etc. and marks items as sold.
Prevents overselling by delisting when inventory reaches zero.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.platform_connectors import get_all_connectors

BUZZ_RELAY_URL = os.getenv("BUZZ_RELAY_URL", "ws://localhost:3000")
BUZZ_PRIVATE_KEY = os.getenv("BUZZ_PRIVATE_KEY")
BOSS_LISTERS_DB = Path(__file__).parent.parent / "boss-listers-ai" / "data.json"
SALES_LOG_FILE = Path(__file__).parent.parent / "crosslist_sales.json"

def post_to_buzz(message, channel="inventory-sync"):
    """Post status to Buzz."""
    if not BUZZ_PRIVATE_KEY:
        print(f"[{datetime.now().isoformat()}] {message}")
        return

    cmd = f"""BUZZ_PRIVATE_KEY={BUZZ_PRIVATE_KEY} BUZZ_RELAY_URL={BUZZ_RELAY_URL} \
    buzz-cli message --channel {channel} '{message}'"""

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ Posted: {message[:50]}...")
    except:
        pass

def load_boss_listers_inventory():
    """Load inventory."""
    if not BOSS_LISTERS_DB.exists():
        return []

    try:
        with open(BOSS_LISTERS_DB) as f:
            return json.load(f).get("products", [])
    except:
        return []

def save_boss_listers_inventory(inventory):
    """Save updated inventory."""
    data = {"products": inventory}
    with open(BOSS_LISTERS_DB, 'w') as f:
        json.dump(data, f, indent=2)

def load_sales_log():
    """Load sales tracking log."""
    if SALES_LOG_FILE.exists():
        try:
            with open(SALES_LOG_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"sales": []}

def save_sales_log(log):
    """Save sales log."""
    with open(SALES_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)

def track_sales(connectors):
    """Poll all platforms for new sales."""
    sales_log = load_sales_log()
    last_check = sales_log.get("last_check", (datetime.now() - timedelta(hours=1)).isoformat())
    since = datetime.fromisoformat(last_check)

    all_sales = []

    for platform_name, connector in connectors.items():
        if not connector.authenticate():
            continue

        try:
            sales = connector.get_sales(since)
            for sale in sales:
                all_sales.append(sale)
                print(f"💰 Sale on {platform_name}: {sale.id}")
        except Exception as e:
            print(f"⚠️ Error fetching {platform_name} sales: {e}")

    return all_sales, since

def update_inventory_for_sales(sales):
    """Update Boss Listers inventory based on sales."""
    inventory = load_boss_listers_inventory()

    sales_processed = []

    for sale in sales:
        product_id = sale.product_id
        quantity_sold = sale.quantity

        # Find product
        product = next((p for p in inventory if p.get("id") == product_id), None)
        if not product:
            continue

        # Update inventory
        current_qty = product.get("quantity", 0)
        new_qty = max(0, current_qty - quantity_sold)
        product["quantity"] = new_qty

        # Mark as sold if out of stock
        if new_qty == 0:
            product["status"] = "sold"
            post_to_buzz(
                f"✅ SOLD OUT: {product.get('name')}\n"
                f"Delisting from all platforms\n"
                f"Sold on: {sale.platform}"
            )

        sales_processed.append({
            "product_id": product_id,
            "product_name": product.get("name"),
            "platform": sale.platform,
            "qty_sold": quantity_sold,
            "new_qty": new_qty,
            "sold_at": sale.sold_at.isoformat() if hasattr(sale.sold_at, 'isoformat') else str(sale.sold_at)
        })

    # Save updated inventory
    save_boss_listers_inventory(inventory)

    return sales_processed

def main():
    """Main agent loop."""
    print("Sales Tracker Agent starting")
    print(f"Relay: {BUZZ_RELAY_URL}")

    post_to_buzz("🤖 Sales Tracker Agent online - monitoring for sales")

    connectors = get_all_connectors()
    print(f"Tracking sales across {len(connectors)} platforms")

    while True:
        try:
            print(f"\n[{datetime.now().isoformat()}] Checking for sales...")

            # Fetch sales from all platforms
            sales, check_time = track_sales(connectors)

            if sales:
                print(f"Found {len(sales)} sales")

                # Update inventory
                processed = update_inventory_for_sales(sales)

                for sale_record in processed:
                    post_to_buzz(
                        f"💸 Sale: {sale_record['product_name']}\n"
                        f"Platform: {sale_record['platform'].capitalize()}\n"
                        f"Qty sold: {sale_record['qty_sold']}\n"
                        f"Remaining: {sale_record['new_qty']}"
                    )

                # Update sales log
                log = load_sales_log()
                log["last_check"] = check_time.isoformat()
                log["sales"].extend(processed)
                save_sales_log(log)
            else:
                print("No new sales detected")

            # Poll interval
            time.sleep(300)  # Check every 5 minutes

        except KeyboardInterrupt:
            post_to_buzz("🛑 Sales Tracker Agent stopping")
            break
        except Exception as e:
            print(f"Agent error: {e}")
            post_to_buzz(f"⚠️ Tracking error: {str(e)[:100]}")
            time.sleep(60)

if __name__ == "__main__":
    main()
