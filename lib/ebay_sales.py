"""
lib/ebay_sales.py — real eBay sales tracking via the Sell Fulfillment API.

Replaces the fake platform_connectors.py sync agents disabled 2026-08-20
(see CLAUDE.md's "platform_connectors.py audited, found non-functional")
with something that actually calls a real eBay endpoint. Mirrors
lib/ebay_listing.py's architecture: injectable transport, dataclass
results, structured errors — the canonical eBay client this project uses.

Endpoint: GET {base}/sell/fulfillment/v1/order
Scope:    https://api.ebay.com/oauth/api_scope/sell.fulfillment
          (eBay's own docs also show the short form "sell.fulfil" in some
          examples — the fully-qualified scope URL is the safe one to
          request; the same access token already used for
          sell.inventory/sell.account should be re-consented to include
          this scope, same pattern as when sell.account was added earlier
          in this project — see lib/ebay_listing.py's history).
Filter:   creationdate:[ISO8601_START..ISO8601_END] — eBay only returns
          orders up to 2 years old; do not set a start date further back.

[Likely, not yet exercised against a live response as of 2026-08-20 —
written from eBay's documented API shape (developer.ebay.com/api-docs/
sell/fulfillment), not yet run against a real order. Field names for
lineItems (sku, legacyItemId, lineItemId) and pricingSummary.total are
confirmed from eBay's own docs; verify the exact response shape the first
time this actually runs against a live account with real orders.]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from urllib.parse import quote

EBAY_BASE_URL = "https://api.ebay.com"
EBAY_SANDBOX_BASE_URL = "https://api.sandbox.ebay.com"

#: The scope this client needs. Must be included in the OAuth consent the
#: refresh token was originally granted with — requesting it at refresh
#: time for a token that was never consented with it fails with HTTP 400,
#: not a helpful "missing scope" message (confirmed the hard way once
#: already for sell.account, see lib/ebay_listing.py).
FULFILLMENT_SCOPE = "https://api.ebay.com/oauth/api_scope/sell.fulfillment"

#: eBay will not return orders older than this, regardless of the filter.
MAX_ORDER_AGE_DAYS = 730


class EbaySalesError(RuntimeError):
    """A sales-fetch attempt failed. Carries eBay's HTTP status and body so
    a caller can distinguish "no orders in this window" (200, empty list)
    from a real failure (auth, scope, rate limit)."""

    def __init__(self, step: str, message: str, *,
                 status: Optional[int] = None, body: Any = None) -> None:
        super().__init__(f"{step}: {message}")
        self.step = step
        self.status = status
        self.body = body


@dataclass(frozen=True)
class SaleLineItem:
    """One sold item within an order — orders can contain multiple SKUs."""
    sku: str
    legacy_item_id: str
    line_item_id: str
    quantity: int
    title: str


@dataclass(frozen=True)
class Sale:
    """One real eBay order, normalised to what this project's inventory
    sync actually needs: which SKUs sold, how many, for how much."""
    order_id: str
    creation_date: str  # ISO 8601, as returned by eBay — not reparsed here
    fulfillment_status: str
    total_value: str
    total_currency: str
    buyer_username: str
    line_items: list[SaleLineItem] = field(default_factory=list)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class EbaySalesClient:
    """Fetches real eBay orders through the Sell Fulfillment API.

    `transport` is injectable so the flow can be tested without credentials
    or network — same convention as EbayListingClient. It receives
    (method, url, headers) and must return an object exposing
    `.status_code` and `.json()`.
    """

    def __init__(self, access_token: str,
                 transport: Optional[Callable[..., Any]] = None,
                 sandbox: bool = False) -> None:
        if not str(access_token or "").strip():
            raise EbaySalesError("config", "access_token is required "
                                 "(OAuth user token with sell.fulfillment scope)")
        self.access_token = access_token
        self.base_url = EBAY_SANDBOX_BASE_URL if sandbox else EBAY_BASE_URL
        self._transport = transport or _requests_transport

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def get_orders_since(self, since: datetime, *,
                         until: Optional[datetime] = None,
                         limit: int = 50) -> list[Sale]:
        """Fetch all orders created on or after `since`. Paginates
        automatically until eBay reports no further pages.

        Raises EbaySalesError naming the failing step — never returns a
        partial result silently on a mid-pagination failure, since a
        caller using this for inventory sync must not treat a truncated
        fetch as "these are all the sales."
        """
        age_days = (datetime.now(timezone.utc) - since.astimezone(timezone.utc)).days
        if age_days > MAX_ORDER_AGE_DAYS:
            raise EbaySalesError(
                "config",
                f"since is {age_days} days ago — eBay does not return orders "
                f"older than {MAX_ORDER_AGE_DAYS} days")

        date_range = f"{_iso(since)}.." + (f"{_iso(until)}" if until else "")
        filter_param = f"creationdate:[{date_range}]"

        sales: list[Sale] = []
        offset = 0
        while True:
            url = (f"{self.base_url}/sell/fulfillment/v1/order"
                   f"?filter={quote(filter_param, safe='[]:.')}"
                   f"&limit={limit}&offset={offset}")
            response = self._transport("GET", url, self._headers())
            status = getattr(response, "status_code", None)
            if status != 200:
                raise EbaySalesError(
                    "getOrders", f"eBay returned HTTP {status}",
                    status=status, body=_safe_body(response))

            body = response.json()
            orders = body.get("orders", [])
            for order in orders:
                sales.append(_parse_order(order))

            offset += len(orders)
            total = body.get("total", 0)
            if offset >= total or not orders:
                break

        return sales


def _parse_order(order: dict) -> Sale:
    pricing = order.get("pricingSummary", {}).get("total", {})
    line_items = [
        SaleLineItem(
            sku=li.get("sku", ""),
            legacy_item_id=li.get("legacyItemId", ""),
            line_item_id=li.get("lineItemId", ""),
            quantity=int(li.get("quantity", 1)),
            title=li.get("title", ""),
        )
        for li in order.get("lineItems", [])
    ]
    return Sale(
        order_id=order.get("orderId", ""),
        creation_date=order.get("creationDate", ""),
        fulfillment_status=order.get("orderFulfillmentStatus", ""),
        total_value=str(pricing.get("value", "")),
        total_currency=pricing.get("currency", ""),
        buyer_username=order.get("buyer", {}).get("username", ""),
        line_items=line_items,
    )


def _safe_body(response: Any) -> Any:
    try:
        return response.json()
    except Exception:
        return getattr(response, "text", None)


def resolve_sku_from_legacy_item_id(legacy_item_id: str) -> str:
    """Resolve eBay's legacy_item_id to the products table SKU format.

    eBay Browse API returns legacy_item_id (e.g., "198079646764").
    products table stores SKU as "v1|{legacy_item_id}|0" (the Inventory API format).

    This reconciler bridges the two. In real use, this will query Supabase to
    verify the SKU actually exists before recording a sale.
    """
    if not legacy_item_id or not str(legacy_item_id).strip():
        raise EbaySalesError(
            "sku_resolution",
            f"legacy_item_id is required, got: {legacy_item_id!r}"
        )

    # Convert to the Inventory API SKU format
    sku = f"v1|{legacy_item_id}|0"
    return sku


def _requests_transport(method: str, url: str, headers: dict[str, str]) -> Any:
    import requests
    return requests.request(method, url, headers=headers, timeout=30)
