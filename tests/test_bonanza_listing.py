"""Tests for lib/bonanza_listing.py — Bonanza marketplace integration."""

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
)


class FakeResponse:
    """Mock HTTP response."""

    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def make_fake_transport(responses):
    """Create a fake transport that returns pre-canned responses."""
    calls = []

    def transport(method, url, data=None, token=""):
        calls.append({"method": method, "url": url, "data": data, "token": token})
        if not responses:
            raise AssertionError(f"unexpected extra call: {method} {url}")
        return responses.pop(0)

    transport.calls = calls
    return transport


class TestBonanzaListingValidation:
    """Validate BonanzaListing data before submission."""

    def test_valid_listing(self):
        """Valid listing passes validation."""
        listing = BonanzaListing(
            title="Vintage collectible card",
            description="Rare vintage card in good condition",
            price=Decimal("49.99"),
            quantity=1,
            sku="CARD-001",
            category_id="1234",
        )
        listing.validate()  # Should not raise

    def test_title_too_short(self):
        """Title must be >= 5 characters."""
        listing = BonanzaListing(
            title="Old",
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id="1234",
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "title must be 5-120 chars" in str(exc.value)

    def test_title_too_long(self):
        """Title must be <= 120 characters."""
        listing = BonanzaListing(
            title="x" * 121,
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id="1234",
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "title must be 5-120 chars" in str(exc.value)

    def test_price_zero_rejected(self):
        """Price must be > 0."""
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("0"),
            quantity=1,
            sku="SKU",
            category_id="1234",
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "price must be > 0" in str(exc.value)

    def test_quantity_zero_rejected(self):
        """Quantity must be >= 1."""
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("10"),
            quantity=0,
            sku="SKU",
            category_id="1234",
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "quantity must be >= 1" in str(exc.value)

    def test_invalid_condition(self):
        """Condition must be one of new|like_new|good|acceptable."""
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id="1234",
            condition="mint",
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "condition must be" in str(exc.value)

    def test_too_many_tags(self):
        """Max 5 tags."""
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id="1234",
            tags=["a", "b", "c", "d", "e", "f"],
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "max 5 tags" in str(exc.value)

    def test_too_many_images(self):
        """Max 12 images."""
        listing = BonanzaListing(
            title="Valid title",
            description="desc",
            price=Decimal("10"),
            quantity=1,
            sku="SKU",
            category_id="1234",
            image_urls=[f"https://example.com/img{i}.jpg" for i in range(13)],
        )
        with pytest.raises(BonanzaError) as exc:
            listing.validate()
        assert "max 12 images" in str(exc.value)


class TestBonanzaListingClient:
    """Test BonanzaListingClient operations."""

    def test_client_requires_token(self):
        """Client initialization requires access token."""
        with pytest.raises(BonanzaError) as exc:
            BonanzaListingClient("")
        assert "access_token" in str(exc.value).lower()

    def test_dry_run_create_listing(self):
        """Dry-run mode returns payload without network call."""
        client = BonanzaListingClient("test_token_123")
        listing = BonanzaListing(
            title="Test listing",
            description="Test",
            price=Decimal("19.99"),
            quantity=2,
            sku="TEST-001",
            category_id="5000",
        )

        result = client.create_listing(listing, dry_run=True)

        assert result["status"] == "dry_run"
        assert result["payload"]["title"] == "Test listing"
        assert result["payload"]["price"] == 19.99

    def test_live_create_listing_success(self):
        """Live create succeeds with valid response."""
        response = {"listing_id": "999888777", "url": "https://bonanza.com/listings/999888777"}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("test_token", transport=transport)

        listing = BonanzaListing(
            title="Real listing",
            description="Actual item",
            price=Decimal("99.99"),
            quantity=1,
            sku="REAL-001",
            category_id="5000",
        )

        result = client.create_listing(listing, dry_run=False)

        assert isinstance(result, BonanzaListingResult)
        assert result.listing_id == "999888777"
        assert "bonanza.com/listings/999888777" in result.url

    def test_live_create_listing_no_id_returned(self):
        """API success but no listing_id is an error."""
        response = {"status": "ok"}  # Missing listing_id
        transport = make_fake_transport([response])
        client = BonanzaListingClient("test_token", transport=transport)

        listing = BonanzaListing(
            title="Test Item",
            description="Test Description",
            price=Decimal("10"),
            quantity=1,
            sku="TEST",
            category_id="5000",
        )

        with pytest.raises(BonanzaError) as exc:
            client.create_listing(listing, dry_run=False)
        assert "no listing_id" in str(exc.value)

    def test_live_create_listing_api_error(self):
        """API returns error response."""
        response = {"error": True, "error_message": "Invalid category"}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("test_token", transport=transport)

        listing = BonanzaListing(
            title="Test Item",
            description="Test Description",
            price=Decimal("10"),
            quantity=1,
            sku="TEST",
            category_id="invalid",
        )

        with pytest.raises(BonanzaError) as exc:
            client.create_listing(listing, dry_run=False)
        assert "Invalid category" in str(exc.value)

    def test_dry_run_update_listing(self):
        """Dry-run update returns payload without network call."""
        client = BonanzaListingClient("test_token_123")
        updates = {"price": 24.99, "quantity": 5}

        result = client.update_listing("123456", updates, dry_run=True)

        assert result["status"] == "dry_run"
        assert result["listing_id"] == "123456"
        assert result["updates"]["price"] == 24.99

    def test_live_update_listing_success(self):
        """Live update succeeds."""
        response = {"status": "updated", "listing_id": "123456"}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("test_token", transport=transport)

        result = client.update_listing("123456", {"price": 24.99}, dry_run=False)

        assert result["status"] == "updated"

    def test_dry_run_delete_listing(self):
        """Dry-run delete returns payload without network call."""
        client = BonanzaListingClient("test_token_123")

        result = client.delete_listing("123456", dry_run=True)

        assert result["status"] == "dry_run"
        assert result["listing_id"] == "123456"

    def test_live_delete_listing_success(self):
        """Live delete succeeds."""
        response = {"status": "deleted", "listing_id": "123456"}
        transport = make_fake_transport([response])
        client = BonanzaListingClient("test_token", transport=transport)

        result = client.delete_listing("123456", dry_run=False)

        assert result["status"] == "deleted"


class TestBonanzaListingResult:
    """Test BonanzaListingResult dataclass."""

    def test_result_immutable(self):
        """Result is frozen."""
        result = BonanzaListingResult(
            listing_id="123", url="https://bonanza.com/listings/123"
        )
        with pytest.raises(AttributeError):
            result.listing_id = "456"

    def test_result_fields(self):
        """Result has correct fields."""
        result = BonanzaListingResult(
            listing_id="999", url="https://bonanza.com/listings/999"
        )
        assert result.listing_id == "999"
        assert result.url == "https://bonanza.com/listings/999"
