"""Tests for lib/ebay_sales.py — the real eBay Fulfillment API sales client.

Mirrors tests/ebay/test_ebay_listing.py's structure: injectable fake
transport, no real network, no real credentials.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from lib.ebay_sales import (
    EbaySalesClient, EbaySalesError, Sale, SaleLineItem, MAX_ORDER_AGE_DAYS,
    resolve_sku_from_legacy_item_id,
)


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def make_fake_transport(responses):
    calls = []

    def transport(method, url, headers):
        calls.append((method, url, headers))
        if not responses:
            raise AssertionError(f"unexpected extra call: {method} {url}")
        return responses.pop(0)

    transport.calls = calls
    return transport


ONE_ORDER_PAGE = {
    "total": 1,
    "orders": [{
        "orderId": "ORDER-1",
        "creationDate": "2026-08-01T00:00:00.000Z",
        "orderFulfillmentStatus": "FULFILLED",
        "pricingSummary": {"total": {"value": "24.99", "currency": "USD"}},
        "buyer": {"username": "collector123"},
        "lineItems": [{
            "sku": "CARD-001", "legacyItemId": "198079646764",
            "lineItemId": "LI-1", "quantity": 1, "title": "Test Card",
        }],
    }],
}


def test_requires_access_token():
    with pytest.raises(EbaySalesError) as exc:
        EbaySalesClient(access_token="")
    assert exc.value.step == "config"


def test_rejects_since_older_than_max_age():
    client = EbaySalesClient(access_token="tok", transport=lambda *a: None)
    too_old = datetime.now(timezone.utc) - timedelta(days=MAX_ORDER_AGE_DAYS + 10)
    with pytest.raises(EbaySalesError) as exc:
        client.get_orders_since(too_old)
    assert exc.value.step == "config"


def test_single_page_of_orders_parsed_correctly():
    transport = make_fake_transport([FakeResponse(200, ONE_ORDER_PAGE)])
    client = EbaySalesClient(access_token="tok", transport=transport)

    sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

    assert len(sales) == 1
    sale = sales[0]
    assert isinstance(sale, Sale)
    assert sale.order_id == "ORDER-1"
    assert sale.fulfillment_status == "FULFILLED"
    assert sale.total_value == "24.99"
    assert sale.total_currency == "USD"
    assert sale.buyer_username == "collector123"
    assert len(sale.line_items) == 1
    li = sale.line_items[0]
    assert isinstance(li, SaleLineItem)
    assert li.sku == "CARD-001"
    assert li.legacy_item_id == "198079646764"
    assert li.quantity == 1


def test_pagination_follows_until_total_reached():
    page1 = {"total": 2, "orders": [ONE_ORDER_PAGE["orders"][0]]}
    page2_order = dict(ONE_ORDER_PAGE["orders"][0])
    page2_order["orderId"] = "ORDER-2"
    page2 = {"total": 2, "orders": [page2_order]}

    transport = make_fake_transport([FakeResponse(200, page1), FakeResponse(200, page2)])
    client = EbaySalesClient(access_token="tok", transport=transport)

    sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

    assert [s.order_id for s in sales] == ["ORDER-1", "ORDER-2"]
    assert len(transport.calls) == 2
    # Second call's offset must advance past the first page's results.
    assert "offset=1" in transport.calls[1][1]


def test_empty_result_returns_empty_list_not_error():
    transport = make_fake_transport([FakeResponse(200, {"total": 0, "orders": []})])
    client = EbaySalesClient(access_token="tok", transport=transport)

    sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))
    assert sales == []


def test_non_200_raises_with_step_and_status():
    transport = make_fake_transport([FakeResponse(401, {"errors": ["bad token"]})])
    client = EbaySalesClient(access_token="tok", transport=transport)

    with pytest.raises(EbaySalesError) as exc:
        client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))
    assert exc.value.step == "getOrders"
    assert exc.value.status == 401


def test_partial_pagination_failure_does_not_return_partial_silently():
    """A failure on page 2 must raise, not just return page 1's results —
    a caller doing inventory sync must not treat a truncated fetch as
    "these are all the sales that happened."""
    page1 = {"total": 2, "orders": [ONE_ORDER_PAGE["orders"][0]]}
    transport = make_fake_transport([FakeResponse(200, page1), FakeResponse(500, {})])
    client = EbaySalesClient(access_token="tok", transport=transport)

    with pytest.raises(EbaySalesError):
        client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))


def test_filter_param_uses_creationdate_range_syntax():
    transport = make_fake_transport([FakeResponse(200, {"total": 0, "orders": []})])
    client = EbaySalesClient(access_token="tok", transport=transport)
    since = datetime(2026, 8, 1, tzinfo=timezone.utc)

    client.get_orders_since(since)

    url = transport.calls[0][1]
    assert "creationdate" in url
    assert "2026-08-01" in url


def test_sandbox_flag_uses_sandbox_host():
    transport = make_fake_transport([FakeResponse(200, {"total": 0, "orders": []})])
    client = EbaySalesClient(access_token="tok", transport=transport, sandbox=True)

    client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

    assert "api.sandbox.ebay.com" in transport.calls[0][1]


def test_access_token_sent_as_bearer_header():
    transport = make_fake_transport([FakeResponse(200, {"total": 0, "orders": []})])
    client = EbaySalesClient(access_token="secret-token-123", transport=transport)

    client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

    headers = transport.calls[0][2]
    assert headers["Authorization"] == "Bearer secret-token-123"


def test_multiple_line_items_in_one_order():
    order = dict(ONE_ORDER_PAGE["orders"][0])
    order["lineItems"] = [
        {"sku": "CARD-001", "legacyItemId": "1", "lineItemId": "LI-1", "quantity": 1, "title": "Card A"},
        {"sku": "CARD-002", "legacyItemId": "2", "lineItemId": "LI-2", "quantity": 2, "title": "Card B"},
    ]
    transport = make_fake_transport([FakeResponse(200, {"total": 1, "orders": [order]})])
    client = EbaySalesClient(access_token="tok", transport=transport)

    sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

    assert len(sales[0].line_items) == 2
    assert sales[0].line_items[1].sku == "CARD-002"
    assert sales[0].line_items[1].quantity == 2


class TestSkuResolution:
    """SKU reconciliation: eBay's legacy_item_id → products table format."""

    def test_resolves_legacy_item_id_to_inventory_format(self):
        """legacy_item_id '198079646764' → 'v1|198079646764|0'"""
        sku = resolve_sku_from_legacy_item_id("198079646764")
        assert sku == "v1|198079646764|0"

    def test_numeric_legacy_item_ids(self):
        """Handle numeric IDs as strings."""
        sku = resolve_sku_from_legacy_item_id("123456789")
        assert sku == "v1|123456789|0"

    def test_rejects_empty_legacy_item_id(self):
        """Empty or None IDs must raise, not silently succeed."""
        with pytest.raises(EbaySalesError) as exc:
            resolve_sku_from_legacy_item_id("")
        assert exc.value.step == "sku_resolution"

    def test_rejects_none_legacy_item_id(self):
        with pytest.raises(EbaySalesError) as exc:
            resolve_sku_from_legacy_item_id(None)
        assert exc.value.step == "sku_resolution"

    def test_rejects_whitespace_only_legacy_item_id(self):
        with pytest.raises(EbaySalesError) as exc:
            resolve_sku_from_legacy_item_id("   ")
        assert exc.value.step == "sku_resolution"

    def test_parse_order_reconciles_empty_sku_from_legacy_item_id(self):
        """Classic eBay listings (non-Inventory API) have empty sku + legacy_item_id.
        The parser must reconcile them into the products table format."""
        order_with_empty_sku = {
            "orderId": "ORDER-CLASSIC",
            "creationDate": "2026-08-20T00:00:00.000Z",
            "orderFulfillmentStatus": "FULFILLED",
            "pricingSummary": {"total": {"value": "49.99", "currency": "USD"}},
            "buyer": {"username": "collector456"},
            "lineItems": [{
                "sku": "",  # Empty for classic listings
                "legacyItemId": "198079646764",  # Real legacy ID
                "lineItemId": "LI-CLASSIC",
                "quantity": 1,
                "title": "Vintage Trading Card",
            }],
        }
        transport = make_fake_transport([FakeResponse(200, {"total": 1, "orders": [order_with_empty_sku]})])
        client = EbaySalesClient(access_token="tok", transport=transport)

        sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

        assert len(sales) == 1
        li = sales[0].line_items[0]
        # SKU must be resolved to Inventory API format, not left empty
        assert li.sku == "v1|198079646764|0"
        assert li.legacy_item_id == "198079646764"

    def test_parses_shipping_and_payment_details(self):
        """Shipping address and payment status are captured at order level."""
        order_with_shipping = {
            "orderId": "ORDER-SHIPPED",
            "creationDate": "2026-08-15T00:00:00.000Z",
            "orderFulfillmentStatus": "FULFILLED",
            "orderPaymentStatus": "PAIDFUL",
            "shippingAddress": {
                "city": "Portland",
                "stateOrProvince": "OR",
                "countryCode": "US",
            },
            "pricingSummary": {"total": {"value": "99.99", "currency": "USD"}},
            "buyer": {"username": "buyer789"},
            "lineItems": [{
                "sku": "CARD-GRADED",
                "legacyItemId": "999888777",
                "lineItemId": "LI-GRADED",
                "quantity": 1,
                "title": "PSA 10 Card",
            }],
        }
        transport = make_fake_transport([FakeResponse(200, {"total": 1, "orders": [order_with_shipping]})])
        client = EbaySalesClient(access_token="tok", transport=transport)

        sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

        assert len(sales) == 1
        sale = sales[0]
        assert sale.payment_status == "PAIDFUL"
        assert sale.ship_to_city == "Portland"
        assert sale.ship_to_state == "OR"
        assert sale.ship_to_country_code == "US"

    def test_parses_line_item_condition_and_fulfillment(self):
        """Per-item condition and fulfillment status are captured."""
        order_with_details = {
            "orderId": "ORDER-DETAILED",
            "creationDate": "2026-08-14T00:00:00.000Z",
            "orderFulfillmentStatus": "FULFILLED",
            "pricingSummary": {"total": {"value": "50.00", "currency": "USD"}},
            "buyer": {"username": "collector999"},
            "lineItems": [{
                "sku": "ITEM-USED",
                "legacyItemId": "555444333",
                "lineItemId": "LI-USED",
                "quantity": 1,
                "title": "Used Item",
                "itemUnitPrice": {"condition": "USED"},
                "lineItemFulfillmentStatus": "SHIPPED",
            }],
        }
        transport = make_fake_transport([FakeResponse(200, {"total": 1, "orders": [order_with_details]})])
        client = EbaySalesClient(access_token="tok", transport=transport)

        sales = client.get_orders_since(datetime.now(timezone.utc) - timedelta(days=1))

        assert len(sales) == 1
        li = sales[0].line_items[0]
        assert li.condition == "USED"
        assert li.fulfillment_status == "SHIPPED"
