"""Tests for lib/bonanza_listing.py — Bonanza (Bonapitit) integration.

Rewritten 2026-08-24: the previous version of this file tested a REST API
shape (POST /listings/create, Bearer token) that Bonanza's real API does
not have. These tests now match the real Bonapitit envelope API — one
endpoint, dev_id/cert_id headers, a per-seller token embedded in the
request body — verified against api.bonanza.com/docs.
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib.bonanza_listing import (
    BonanzaError,
    BonanzaListing,
    BonanzaListingClient,
    BonanzaListingResult,
    BonanzaTokenResult,
    fetch_token,
)


def make_fake_transport(responses):
    """Fake transport matching the real signature:
    (dev_id, cert_id, request_name, body) -> response dict."""
    calls = []

    def transport(dev_id, cert_id, request_name, body):
        calls.append({"dev_id": dev_id, "cert_id": cert_id, "request_name": request_name, "body": body})
        if not responses:
            raise AssertionError(f"unexpected extra call: {request_name}")
        return responses.pop(0)

    transport.calls = calls
    return transport


class TestBonanzaListingValidation:
    """Validate BonanzaListing data before submission."""

    def test_valid_listing(self):
        listing = BonanzaListing(
            title="Vintage collectible card",
            description="Rare vintage card in good condition",
            price=Decimal("49.99"),
            quantity=1,
            sku="CARD-001",
            category_id=1234,
        )
        listing.validate()  # Should not raise

    def test_title_missing(self):
        listing = BonanzaListing(
            title="",
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id=1234,
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "title is required" in str(exc.value)

    def test_title_too_long(self):
        """Title must be <= 80 characters (real API limit, not 120)."""
        listing = BonanzaListing(
            title="x" * 81,
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id=1234,
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "max 80 chars" in str(exc.value)

    def test_price_zero_rejected(self):
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("0"),
            quantity=1,
            sku="SKU",
            category_id=1234,
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "price must be > 0" in str(exc.value)

    def test_quantity_zero_rejected(self):
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("10"),
            quantity=0,
            sku="SKU",
            category_id=1234,
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "quantity must be >= 1" in str(exc.value)

    def test_invalid_condition(self):
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id=1234,
            condition="mint",
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "condition must be" in str(exc.value)

    def test_too_many_images(self):
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id=1234,
            image_urls=[f"https://example.com/img{i}.jpg" for i in range(13)],
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "max 12 images" in str(exc.value)

    def test_to_item_payload_shape(self):
        """The item payload must match addFixedPriceItem's real field names —
        primaryCategory.categoryId, itemSpecifics.specifics as a [key, value]
        pair, not guessed flat fields."""
        listing = BonanzaListing(
            title="Test",
            description="desc",
            price=Decimal("24.99"),
            quantity=2,
            sku="SKU-1",
            category_id=5000,
            condition="new",
            image_urls=["https://example.com/a.jpg"],
        )
        payload = listing.to_item_payload()
        assert payload["primaryCategory"] == {"categoryId": 5000}
        assert payload["itemSpecifics"]["specifics"] == [["condition", "new"]]
        assert payload["pictureDetails"]["pictureURL"] == ["https://example.com/a.jpg"]
        assert payload["price"] == 24.99
        assert payload["quantity"] == 2


class TestFetchToken:
    """fetch_token() gets a user token that still needs seller approval."""

    def test_fetch_token_requires_dev_cert(self):
        with pytest.raises(BonanzaError) as exc:
            fetch_token("", "cert")
        assert "dev_id and cert_id required" in str(exc.value)

    def test_fetch_token_success(self):
        transport = make_fake_transport([
            {"authToken": "tok_abc123", "authenticationURL": "https://bonanza.com/auth/xyz", "hardExpirationTime": "2027-08-24"}
        ])
        result = fetch_token("dev1", "cert1", transport=transport)

        assert isinstance(result, BonanzaTokenResult)
        assert result.auth_token == "tok_abc123"
        assert result.authentication_url == "https://bonanza.com/auth/xyz"
        assert transport.calls[0]["request_name"] == "fetchToken"
        assert transport.calls[0]["dev_id"] == "dev1"

    def test_fetch_token_missing_fields(self):
        transport = make_fake_transport([{}])
        with pytest.raises(BonanzaError) as exc:
            fetch_token("dev1", "cert1", transport=transport)
        assert "missing authToken" in str(exc.value)


class TestBonanzaListingClient:
    """Test BonanzaListingClient operations against the real envelope API."""

    def test_client_requires_dev_and_cert(self):
        with pytest.raises(BonanzaError) as exc:
            BonanzaListingClient("", "", "token")
        assert "dev_id and cert_id required" in str(exc.value)

    def test_client_requires_token(self):
        with pytest.raises(BonanzaError) as exc:
            BonanzaListingClient("dev1", "cert1", "")
        assert "access_token" in str(exc.value).lower()

    def test_dry_run_create_listing(self):
        """Dry-run mode returns the real envelope payload without a network call."""
        client = BonanzaListingClient("dev1", "cert1", "test_token_123")
        listing = BonanzaListing(
            title="Test listing",
            description="Test",
            price=Decimal("19.99"),
            quantity=2,
            sku="TEST-001",
            category_id=5000,
        )

        result = client.create_listing(listing, dry_run=True)

        assert result["status"] == "dry_run"
        assert result["payload"]["requesterCredentials"]["bonanzleAuthToken"] == "test_token_123"
        assert result["payload"]["item"]["title"] == "Test listing"
        assert result["payload"]["item"]["price"] == 19.99

    def test_live_create_listing_success(self):
        """Live create succeeds — real response uses itemId/sellingState, not listing_id."""
        response = {"itemId": 999888777, "sellingState": "Active"}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("dev1", "cert1", "test_token", transport=transport)

        listing = BonanzaListing(
            title="Real listing",
            description="Actual item",
            price=Decimal("99.99"),
            quantity=1,
            sku="REAL-001",
            category_id=5000,
        )

        result = client.create_listing(listing, dry_run=False)

        assert isinstance(result, BonanzaListingResult)
        assert result.listing_id == "999888777"
        assert result.selling_state == "Active"
        assert "999888777" in result.url
        assert transport.calls[0]["request_name"] == "addFixedPriceItem"

    def test_live_create_listing_no_id_returned(self):
        response = {"sellingState": "Unknown"}  # Missing itemId
        transport = make_fake_transport([response])
        client = BonanzaListingClient("dev1", "cert1", "test_token", transport=transport)

        listing = BonanzaListing(
            title="Test Item", description="Test Description", price=Decimal("10"),
            quantity=1, sku="TEST", category_id=5000,
        )

        with pytest.raises(BonanzaError) as exc:
            client.create_listing(listing, dry_run=False)
        assert "no itemId" in str(exc.value)

    def test_live_create_listing_api_error(self):
        """Real API errors surface via errorMessage, not error/error_message."""
        response = {"errorMessage": "Invalid category"}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("dev1", "cert1", "test_token", transport=transport)

        listing = BonanzaListing(
            title="Test Item", description="Test Description", price=Decimal("10"),
            quantity=1, sku="TEST", category_id=999999,
        )

        with pytest.raises(BonanzaError) as exc:
            client.create_listing(listing, dry_run=False)
        assert "Invalid category" in str(exc.value)

    def test_dry_run_update_listing(self):
        client = BonanzaListingClient("dev1", "cert1", "test_token_123")
        result = client.update_listing("123456", {"price": 24.99}, dry_run=True)

        assert result["status"] == "dry_run"
        assert result["listing_id"] == "123456"

    def test_live_update_listing_success(self):
        response = {"itemId": 123456}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("dev1", "cert1", "test_token", transport=transport)

        result = client.update_listing("123456", {"price": 24.99}, dry_run=False)

        assert result["itemId"] == 123456
        assert transport.calls[0]["request_name"] == "reviseFixedPriceItem"
        assert transport.calls[0]["body"]["item"]["itemId"] == 123456

    def test_dry_run_delete_listing(self):
        client = BonanzaListingClient("dev1", "cert1", "test_token_123")
        result = client.delete_listing("123456", dry_run=True)

        assert result["status"] == "dry_run"
        assert result["listing_id"] == "123456"

    def test_live_delete_listing_success(self):
        response = {"itemId": 123456}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("dev1", "cert1", "test_token", transport=transport)

        result = client.delete_listing("123456", dry_run=False)

        assert transport.calls[0]["request_name"] == "endFixedPriceItem"
        assert transport.calls[0]["body"]["itemId"] == 123456


class TestBonanzaListingResult:
    """Test BonanzaListingResult dataclass."""

    def test_result_immutable(self):
        result = BonanzaListingResult(listing_id="123", selling_state="Active", url="https://www.bonanza.com/booths/items/123")
        with pytest.raises(AttributeError):
            result.listing_id = "456"

    def test_result_fields(self):
        result = BonanzaListingResult(listing_id="999", selling_state="Active", url="https://www.bonanza.com/booths/items/999")
        assert result.listing_id == "999"
        assert result.selling_state == "Active"
        assert "999" in result.url
