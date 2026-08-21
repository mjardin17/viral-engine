#!/usr/bin/env python3
"""SalesTrackerAgent — polls eBay orders, records sales to Supabase atomically.

Runs every 5 minutes. Fetches orders since last poll, resolves SKU to products
table, decrements inventory, logs sales. Uses Supabase RPC for atomicity.

Ready to run as soon as eBay token is refreshed.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass

import supabase

from lib.ebay_sales import EbaySalesClient, resolve_sku_from_legacy_item_id


@dataclass
class SalesTrackerState:
    last_poll: datetime
    sales_count: int
    error_count: int


class SalesTrackerAgent:
    def __init__(self, ebay_token: str, supabase_url: str, supabase_key: str):
        self.ebay = EbaySalesClient(ebay_token)
        self.sb = supabase.create_client(supabase_url, supabase_key)
        self.state_file = Path(".state/sales_tracker.json")
        self.state_file.parent.mkdir(exist_ok=True)

    def run(self):
        """Poll eBay for new orders, record sales to Supabase."""
        state = self._load_state()

        try:
            since = state.last_poll
            orders = self.ebay.get_orders_since(since)

            for sale in orders:
                self._record_sale(sale)
                state.sales_count += 1

            state.last_poll = datetime.now(timezone.utc)
            self._save_state(state)

        except Exception as e:
            state.error_count += 1
            self._save_state(state)
            raise

        return state

    def _record_sale(self, sale):
        """Atomically record a sale: resolve SKU, decrement quantity, log."""
        for item in sale.line_items:
            # Resolve eBay's legacy_item_id to products table SKU format
            sku = resolve_sku_from_legacy_item_id(item.legacy_item_id)

            # Call Supabase RPC to atomically:
            # 1. Find product by SKU
            # 2. Decrement quantity by item.quantity
            # 3. Log sale to sync_logs
            # Fails safely if SKU not found (prevents silent partial sales)
            result = self.sb.rpc(
                "record_sale",
                {
                    "p_sku": sku,
                    "p_quantity": item.quantity,
                    "p_order_id": sale.order_id,
                    "p_source": "ebay",
                    "p_total_value": float(sale.total_value),
                    "p_currency": sale.total_currency,
                    "p_buyer": sale.buyer_username,
                },
            ).execute()

            if not result.data:
                raise ValueError("SKU not found in products: {}".format(sku))

    def _load_state(self):
        """Load last poll time, default to 24 hours ago."""
        if not self.state_file.exists():
            return SalesTrackerState(
                last_poll=datetime.now(timezone.utc) - timedelta(days=1),
                sales_count=0,
                error_count=0,
            )

        with open(self.state_file) as f:
            data = json.load(f)
            return SalesTrackerState(
                last_poll=datetime.fromisoformat(data["last_poll"]),
                sales_count=data["sales_count"],
                error_count=data["error_count"],
            )

    def _save_state(self, state):
        """Persist state for next run."""
        with open(self.state_file, "w") as f:
            json.dump(
                {
                    "last_poll": state.last_poll.isoformat(),
                    "sales_count": state.sales_count,
                    "error_count": state.error_count,
                },
                f,
            )


if __name__ == "__main__":
    token = os.environ.get("EBAY_REFRESH_TOKEN")
    if not token:
        print("ERROR: EBAY_REFRESH_TOKEN not set")
        exit(1)

    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = os.environ.get("SUPABASE_ANON_KEY")
    if not sb_url or not sb_key:
        print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY required")
        exit(1)

    agent = SalesTrackerAgent(token, sb_url, sb_key)
    state = agent.run()
    print("Success: {} sales recorded".format(state.sales_count))
