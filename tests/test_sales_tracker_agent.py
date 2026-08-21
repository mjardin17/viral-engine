"""Unit tests for agents/sales_tracker_agent.py — no real credentials needed."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.sales_tracker_agent import SalesTrackerAgent, SalesTrackerState
from lib.ebay_sales import Sale, SaleLineItem


class FakeSB:
    def __init__(self):
        self.recorded = []

    def rpc(self, name, params):
        if name == "record_sale":
            self.recorded.append(params)
            return self

        return self

    def execute(self):
        result = MagicMock()
        result.data = True  # Assume success unless test modifies
        return result


class FakeEbay:
    def __init__(self, sales=None):
        self.sales = sales or []

    def get_orders_since(self, since):
        return self.sales


@pytest.fixture
def tmp_state_dir(tmp_path):
    """Temporary state directory for tests."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    yield state_dir


def test_records_sale_to_supabase(tmp_state_dir):
    """Agent fetches orders and calls Supabase RPC."""
    fake_sb = FakeSB()
    fake_ebay = FakeEbay(
        sales=[
            Sale(
                order_id="ORDER-1",
                creation_date="2026-08-21T00:00:00Z",
                fulfillment_status="FULFILLED",
                total_value="24.99",
                total_currency="USD",
                buyer_username="buyer123",
                line_items=[
                    SaleLineItem(
                        sku="CARD-001",
                        legacy_item_id="198079646764",
                        line_item_id="LI-1",
                        quantity=1,
                        title="Test Card",
                    )
                ],
            )
        ]
    )

    with patch.object(Path, "mkdir"), patch.object(Path, "exists", return_value=False):
        agent = SalesTrackerAgent("tok", "http://localhost", "key")
        agent.sb = fake_sb
        agent.ebay = fake_ebay
        agent.state_file = tmp_state_dir / "sales_tracker.json"

        state = agent.run()

    assert state.sales_count == 1
    assert len(fake_sb.recorded) == 1
    assert fake_sb.recorded[0]["p_sku"] == "v1|198079646764|0"


def test_resolves_legacy_item_id_to_inventory_sku(tmp_state_dir):
    """Sale with legacy_item_id gets resolved to v1|{id}|0 format."""
    fake_sb = FakeSB()
    fake_ebay = FakeEbay(
        sales=[
            Sale(
                order_id="ORDER-2",
                creation_date="2026-08-21T00:00:00Z",
                fulfillment_status="FULFILLED",
                total_value="50.00",
                total_currency="USD",
                buyer_username="buyer456",
                line_items=[
                    SaleLineItem(
                        sku="",  # Empty SKU from Fulfillment API
                        legacy_item_id="123456789",  # Real legacy ID
                        line_item_id="LI-2",
                        quantity=2,
                        title="Vintage Card",
                    )
                ],
            )
        ]
    )

    with patch.object(Path, "mkdir"), patch.object(Path, "exists", return_value=False):
        agent = SalesTrackerAgent("tok", "http://localhost", "key")
        agent.sb = fake_sb
        agent.ebay = fake_ebay
        agent.state_file = tmp_state_dir / "sales_tracker.json"

        state = agent.run()

    recorded = fake_sb.recorded[0]
    assert recorded["p_sku"] == "v1|123456789|0"
    assert recorded["p_quantity"] == 2


def test_state_persists_last_poll_time(tmp_state_dir):
    """After run, last_poll is saved for next cycle."""
    fake_sb = FakeSB()
    fake_ebay = FakeEbay(sales=[])

    with patch.object(Path, "mkdir"), patch.object(Path, "exists", return_value=False):
        agent = SalesTrackerAgent("tok", "http://localhost", "key")
        agent.sb = fake_sb
        agent.ebay = fake_ebay
        agent.state_file = tmp_state_dir / "sales_tracker.json"

        state1 = agent.run()
        state1_time = state1.last_poll

        # Load state from disk
        with open(agent.state_file) as f:
            saved = json.load(f)

        assert saved["last_poll"] == state1_time.isoformat()


def test_handles_multiple_line_items_per_order(tmp_state_dir):
    """Order with 2 items results in 2 RPC calls."""
    fake_sb = FakeSB()
    fake_ebay = FakeEbay(
        sales=[
            Sale(
                order_id="ORDER-3",
                creation_date="2026-08-21T00:00:00Z",
                fulfillment_status="FULFILLED",
                total_value="100.00",
                total_currency="USD",
                buyer_username="buyer789",
                line_items=[
                    SaleLineItem(
                        sku="",
                        legacy_item_id="111",
                        line_item_id="LI-A",
                        quantity=1,
                        title="Item A",
                    ),
                    SaleLineItem(
                        sku="",
                        legacy_item_id="222",
                        line_item_id="LI-B",
                        quantity=3,
                        title="Item B",
                    ),
                ],
            )
        ]
    )

    with patch.object(Path, "mkdir"), patch.object(Path, "exists", return_value=False):
        agent = SalesTrackerAgent("tok", "http://localhost", "key")
        agent.sb = fake_sb
        agent.ebay = fake_ebay
        agent.state_file = tmp_state_dir / "sales_tracker.json"

        state = agent.run()

    # 1 order with 2 items = 2 RPC calls
    assert len(fake_sb.recorded) == 2
    assert fake_sb.recorded[0]["p_sku"] == "v1|111|0"
    assert fake_sb.recorded[1]["p_sku"] == "v1|222|0"
    assert fake_sb.recorded[1]["p_quantity"] == 3
