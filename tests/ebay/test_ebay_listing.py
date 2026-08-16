"""Tests for lib/ebay_listing.py — the three-call eBay Inventory API flow.

Emphasis is on the failure modes that have actually bitten this repo:
reporting success when nothing happened, and losing track of which step broke.
"""

import pytest

from lib.ebay_listing import (
    EbayListingClient,
    EbayListingError,
    EbayListingPolicies,
    EbayProduct,
    EbayValidationError,
    build_inventory_item_payload,
    build_offer_payload,
)


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def make_transport(responses):
    """Transport returning queued responses, recording each call."""
    calls = []

    def transport(method, url, headers, body):
        calls.append({"method": method, "url": url, "headers": headers, "body": body})
        if not responses:
            raise AssertionError(f"unexpected extra call: {method} {url}")
        return responses.pop(0)

    transport.calls = calls
    return transport


POLICIES = EbayListingPolicies(
    fulfillment_policy_id="FUL-1",
    payment_policy_id="PAY-1",
    return_policy_id="RET-1",
    merchant_location_key="LOC-1",
)


def make_product(**overrides):
    defaults = dict(
        sku="CARD-001",
        title="2024 Topps Chrome Refractor #123",
        description="Near mint, stored in a sleeve.",
        price="24.99",
        category_id="261328",
        quantity=1,
        condition="USED_EXCELLENT",
        image_urls=("https://example.com/front.jpg",),
    )
    defaults.update(overrides)
    return EbayProduct(**defaults)


# --------------------------------------------------------------------------
# Validation — fail before spending a network call or creating a bad listing
# --------------------------------------------------------------------------

def test_title_over_80_chars_is_rejected_not_truncated():
    with pytest.raises(EbayValidationError, match="80"):
        make_product(title="x" * 81)


def test_category_id_is_required():
    with pytest.raises(EbayValidationError, match="category_id"):
        make_product(category_id="")


def test_unknown_condition_is_rejected():
    with pytest.raises(EbayValidationError, match="condition"):
        make_product(condition="MINTY_FRESH")


def test_local_image_path_is_rejected_because_ebay_fetches_by_url():
    with pytest.raises(EbayValidationError, match="http"):
        make_product(image_urls=("C:/photos/front.jpg",))


def test_price_uses_decimal_so_cents_are_not_truncated():
    # int(1.15 * 100) == 114 in float math; Decimal must keep 1.15 -> "1.15".
    assert make_product(price=1.15).price == "1.15"
    assert make_product(price=0.29).price == "0.29"
    assert make_product(price="24.9").price == "24.90"


def test_zero_or_negative_price_is_rejected():
    with pytest.raises(EbayValidationError, match="positive"):
        make_product(price="0")
    with pytest.raises(EbayValidationError, match="positive"):
        make_product(price="-5")


def test_policies_require_every_id():
    with pytest.raises(EbayValidationError, match="return_policy_id"):
        EbayListingPolicies("FUL", "PAY", "", "LOC")


# --------------------------------------------------------------------------
# Payload shape — price belongs on the offer, never the inventory item
# --------------------------------------------------------------------------

def test_inventory_item_payload_carries_no_price():
    payload = build_inventory_item_payload(make_product())
    assert "price" not in json_flat(payload), (
        "price must not appear on the inventory item — it belongs to the offer"
    )
    assert payload["availability"]["shipToLocationAvailability"]["quantity"] == 1
    assert payload["condition"] == "USED_EXCELLENT"


def test_offer_payload_carries_price_category_and_policies():
    payload = build_offer_payload(make_product(), POLICIES)
    assert payload["pricingSummary"]["price"] == {"value": "24.99", "currency": "USD"}
    assert payload["categoryId"] == "261328"
    assert payload["listingPolicies"]["fulfillmentPolicyId"] == "FUL-1"
    assert payload["merchantLocationKey"] == "LOC-1"
    assert payload["format"] == "FIXED_PRICE"


def json_flat(obj) -> str:
    import json
    return json.dumps(obj)


# --------------------------------------------------------------------------
# Flow
# --------------------------------------------------------------------------

def test_dry_run_sends_nothing_and_is_not_published():
    transport = make_transport([])
    client = EbayListingClient("token", transport=transport)

    result = client.create_listing(make_product(), POLICIES, dry_run=True)

    assert transport.calls == []
    assert result.dry_run is True
    assert result.listing_id is None
    assert result.published is False, "a dry run must never report as published"
    assert "inventory_item" in result.payloads and "offer" in result.payloads


def test_happy_path_makes_all_three_calls_in_order():
    transport = make_transport([
        FakeResponse(204),
        FakeResponse(201, {"offerId": "OFFER-9"}),
        FakeResponse(200, {"listingId": "LISTING-42"}),
    ])
    client = EbayListingClient("token", transport=transport)

    result = client.create_listing(make_product(), POLICIES, dry_run=False)

    methods = [(c["method"], c["url"].rsplit("/sell/inventory/v1", 1)[1])
               for c in transport.calls]
    assert methods == [
        ("PUT", "/inventory_item/CARD-001"),
        ("POST", "/offer"),
        ("POST", "/offer/OFFER-9/publish"),
    ]
    assert result.listing_id == "LISTING-42"
    assert result.offer_id == "OFFER-9"
    assert result.published is True


def test_inventory_item_call_sends_content_language_header():
    transport = make_transport([
        FakeResponse(204),
        FakeResponse(201, {"offerId": "O"}),
        FakeResponse(200, {"listingId": "L"}),
    ])
    EbayListingClient("token", transport=transport).create_listing(
        make_product(), POLICIES, dry_run=False,
    )
    # Omitting this yields a 400 whose message never mentions the header.
    assert transport.calls[0]["headers"]["Content-Language"] == "en-US"


def test_failure_at_step_one_names_the_step_and_stops():
    transport = make_transport([FakeResponse(401, {"errors": ["bad token"]})])
    client = EbayListingClient("token", transport=transport)

    with pytest.raises(EbayListingError) as exc:
        client.create_listing(make_product(), POLICIES, dry_run=False)

    assert exc.value.step == "createOrReplaceInventoryItem"
    assert exc.value.status == 401
    assert len(transport.calls) == 1, "must not continue after a failed step"


def test_offer_accepted_but_no_offer_id_is_an_error_not_a_silent_pass():
    transport = make_transport([
        FakeResponse(204),
        FakeResponse(201, {}),  # 201 but no offerId
    ])
    client = EbayListingClient("token", transport=transport)

    with pytest.raises(EbayListingError) as exc:
        client.create_listing(make_product(), POLICIES, dry_run=False)

    assert exc.value.step == "createOffer"
    assert len(transport.calls) == 2, "must not attempt publish without an offerId"


def test_publish_without_listing_id_reports_the_unpublished_offer():
    """The dangerous middle state: an offer exists but is not live."""
    transport = make_transport([
        FakeResponse(204),
        FakeResponse(201, {"offerId": "OFFER-7"}),
        FakeResponse(200, {}),  # 200 but no listingId
    ])
    client = EbayListingClient("token", transport=transport)

    with pytest.raises(EbayListingError) as exc:
        client.create_listing(make_product(), POLICIES, dry_run=False)

    assert exc.value.step == "publishOffer"
    # The message must name the orphaned offer so a human can recover it.
    assert "OFFER-7" in str(exc.value)
    assert "NOT live" in str(exc.value)


def test_publish_failure_does_not_report_a_listing():
    transport = make_transport([
        FakeResponse(204),
        FakeResponse(201, {"offerId": "OFFER-7"}),
        FakeResponse(400, {"errors": [{"message": "missing shipping policy"}]}),
    ])
    client = EbayListingClient("token", transport=transport)

    with pytest.raises(EbayListingError) as exc:
        client.create_listing(make_product(), POLICIES, dry_run=False)

    assert exc.value.step == "publishOffer"
    assert exc.value.body == {"errors": [{"message": "missing shipping policy"}]}


def test_empty_access_token_is_rejected_at_construction():
    with pytest.raises(EbayValidationError, match="access_token"):
        EbayListingClient("")


def test_sandbox_flag_switches_host():
    client = EbayListingClient("t", transport=make_transport([]), sandbox=True)
    assert "sandbox" in client.base_url


# --------------------------------------------------------------------------
# Regressions found by review after the module had already been written.
# --------------------------------------------------------------------------

def test_infinite_price_is_rejected_not_sent_to_ebay_as_Infinity():
    """Decimal('Infinity') <= 0 is False — this once reached pricingSummary."""
    with pytest.raises(EbayValidationError, match="finite"):
        make_product(price=float("inf"))


def test_nan_price_raises_our_error_type():
    with pytest.raises(EbayValidationError):
        make_product(price=float("nan"))


def test_half_cent_rounds_up_not_to_even():
    assert make_product(price="0.125").price == "0.13"
    assert make_product(price="2.005").price == "2.01"


def test_listing_with_no_images_is_rejected_locally():
    """eBay won't publish a pictureless listing; fail with a message that says so."""
    with pytest.raises(EbayValidationError, match="image"):
        make_product(image_urls=())
