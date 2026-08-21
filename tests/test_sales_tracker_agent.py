"""Tests for agents/sales_tracker_agent.py — eBay sales tracking to Supabase."""

import sys
import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.sales_tracker_agent import (
    SalesTrackerAgent,
    SalesTrackerState,
    SupabaseSalesWriter,
)
from lib.ebay_sales import Sale, SaleLineItem, EbaySalesError


class FakeEbayClient:
    """Fake eBay client for testing."""
    def __init__(self, orders=None, sandbox=False):
        self.orders = orders or []
        self.sandbox = sandbox
        self.calls = []

    def get_orders_since(self, since):
        self.calls.append(("get_orders_since", since))
        return self.orders


class FakeSupabaseClient:
    """Fake Supabase client for testing."""
    def __init__(self):
        self.rpc_calls = []
        self.rpc_results = {}

    def rpc(self, method, params):
        self.rpc_calls.append((method, params))
        result = MagicMock()
        result.data = self.rpc_results.get(method, [{"status": "recorded"}])
        result.execute = lambda: result
        return result


class TestSalesTrackerState:
    """Test state persistence."""

    def test_save_and_load(self, tmp_path):
        """State persists to JSON and reloads correctly."""
        state_file = tmp_path / "state.json"

        state1 = SalesTrackerState()
        state1.last_poll_time = "2026-08-21T12:00:00+00:00"
        state1.processed_orders = {"ORDER-1": "v1|198079646764|0"}
        state1.save(state_file)

        state2 = SalesTrackerState.load(state_file)
        assert state2.last_poll_time == "2026-08-21T12:00:00+00:00"
        assert state2.processed_orders == {"ORDER-1": "v1|198079646764|0"}

    def test_load_creates_default_if_missing(self, tmp_path):
        """Missing state file returns defaults (last_poll = 24h ago)."""
        state_file = tmp_path / "nonexistent.json"
        state = SalesTrackerState.load(state_file)

        # last_poll should be ~24h ago
        parsed = datetime.fromisoformat(state.last_poll_time)
        now = datetime.now(timezone.utc)
        delta = (now - parsed).total_seconds()
        assert 85000 < delta < 90000  # ~24h ± 1min


class TestSupabaseSalesWriter:
    """Test Supabase RPC-based sales recording."""

    def test_record_sale_calls_rpc_with_correct_params(self):
        """record_sale() calls RPC with order/SKU/qty/price."""
        client = FakeSupabaseClient()
        writer = SupabaseSalesWriter("http://localhost", "key")
        writer._client = client

        writer.record_sale(
            order_id="ORDER-1",
            sku="v1|198079646764|0",
            quantity=1,
            total_price="24.99"
        )

        assert len(client.rpc_calls) == 1
        method, params = client.rpc_calls[0]
        assert method == "record_sale"
        assert params["p_order_id"] == "ORDER-1"
        assert params["p_sku"] == "v1|198079646764|0"
        assert params["p_quantity"] == 1
        assert params["p_total_price"] == 24.99


class TestSalesTrackerAgent:
    """Test order polling and sales recording."""

    def test_poll_fetches_orders_since_last_poll(self, tmp_path):
        """poll_and_record() fetches orders from last_poll_time."""
        state_file = tmp_path / "state.json"

        fake_ebay = FakeEbayClient(orders=[])
        agent = SalesTrackerAgent(
            ebay_access_token="tok",
            supabase_url="http://localhost",
            supabase_anon_key="key",
            ebay_transport=lambda m, u, h: None,
            state_file=state_file,
            sandbox=True
        )
        agent.ebay_client = fake_ebay

        result = agent.poll_and_record()

        assert result["status"] == "no_orders"
        assert result["orders_processed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
