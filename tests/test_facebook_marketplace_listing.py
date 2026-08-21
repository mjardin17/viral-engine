"""Tests for lib/facebook_marketplace_listing.py."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from lib.facebook_marketplace_listing import (
    FacebookMarketplaceError,
    FacebookMarketplaceListingClient,
    FacebookMarketplaceProduct,
    FacebookMarketplaceListingResult,
)


def make_fake_transport(responses):
    """Create fake transport."""
    calls = []

    def transport(method, url, data=None, token=""):
        calls.append({"method": method, "url": url, "data": data})
        if not responses:
            raise AssertionError(f"unexpected call: {method} {url}")
        return responses.pop(0)

    transport.calls = calls
    return transport


class TestFacebookMarketplaceProduct:
    """Validate product data."""

    def test_valid_product(self):
        """Valid product passes."""
        product = FacebookMarketplaceProduct(
            title="Vintage collectible",
            description="Rare item",
            price=Decimal("49.99"),
            sku="COLL-001",
            category="vintage_collectibles",
        )
        product.validate()

    def test_title_too_short(self):
        """Title minimum 5 chars."""
        product = FacebookMarketplaceProduct(
            title="Old",
            description="desc",
            price=Decimal("10"),
            sku="SKU",
            category="vintage",
        )
        with pytest.raises(FacebookMarketplaceError) as exc:
            product.validate()
        assert "5-150 chars" in str(exc.value)

    def test_price_validation(self):
        """Price must be > 0."""
        product = FacebookMarketplaceProduct(
            title="Valid Title",
            description="desc",
            price=Decimal("0"),
            sku="SKU",
            category="vintage",
        )
        with pytest.raises(FacebookMarketplaceError) as exc:
            product.validate()
        assert "price must be > 0" in str(exc.value)

    def test_condition_validation(self):
        """Condition must be valid."""
        product = FacebookMarketplaceProduct(
            title="Valid Title",
            description="desc",
            price=Decimal("10"),
            sku="SKU",
            category="vintage",
            condition="mint",
        )
        with pytest.raises(FacebookMarketplaceError) as exc:
            product.validate()
        assert "condition must be" in str(exc.value)

    def test_image_url_validation(self):
        """Images must be https."""
        product = FacebookMarketplaceProduct(
            title="Valid Title",
            description="desc",
            price=Decimal("10"),
            sku="SKU",
            category="vintage",
            images=["http://example.com/img.jpg"],
        )
        with pytest.raises(FacebookMarketplaceError) as exc:
            product.validate()
        assert "https://" in str(exc.value)

    def test_max_images(self):
        """Max 10 images."""
        product = FacebookMarketplaceProduct(
            title="Valid Title",
            description="desc",
            price=Decimal("10"),
            sku="SKU",
            category="vintage",
            images=[f"https://example.com/img{i}.jpg" for i in range(11)],
        )
        with pytest.raises(FacebookMarketplaceError) as exc:
            product.validate()
        assert "max 10 images" in str(exc.value)


class TestFacebookMarketplaceListingClient:
    """Test listing client."""

    def test_client_requires_credentials(self):
        """Client requires token and page_id."""
        with pytest.raises(FacebookMarketplaceError):
            FacebookMarketplaceListingClient("", "123")

        with pytest.raises(FacebookMarketplaceError):
            FacebookMarketplaceListingClient("token", "")

    def test_dry_run_create(self):
        """Dry-run returns payload."""
        client = FacebookMarketplaceListingClient("token", "page123")
        product = FacebookMarketplaceProduct(
            title="Test Product",
            description="Test",
            price=Decimal("19.99"),
            sku="TEST-001",
            category="vintage",
        )

        result = client.create_listing(product, dry_run=True)

        assert result["status"] == "dry_run"
        assert result["payload"]["name"] == "Test Product"
        assert result["payload"]["price"] == 1999  # cents

    def test_live_create_success(self):
        """Live create succeeds."""
        response = {"id": "listing123", "name": "Test"}
        transport = make_fake_transport([response])
        client = FacebookMarketplaceListingClient("token", "page123", transport=transport)

        product = FacebookMarketplaceProduct(
            title="Test Product",
            description="Test",
            price=Decimal("19.99"),
            sku="TEST-001",
            category="vintage",
        )

        result = client.create_listing(product, dry_run=False)

        assert isinstance(result, FacebookMarketplaceListingResult)
        assert result.listing_id == "listing123"
        assert "facebook.com/marketplace" in result.url

    def test_dry_run_update(self):
        """Dry-run update."""
        client = FacebookMarketplaceListingClient("token", "page123")

        result = client.update_listing("123", {"price": 2499}, dry_run=True)

        assert result["status"] == "dry_run"

    def test_dry_run_delete(self):
        """Dry-run delete."""
        client = FacebookMarketplaceListingClient("token", "page123")

        result = client.delete_listing("123", dry_run=True)

        assert result["status"] == "dry_run"


class TestFacebookMarketplaceListingResult:
    """Test result dataclass."""

    def test_result_immutable(self):
        """Result is frozen."""
        result = FacebookMarketplaceListingResult(
            listing_id="123",
            product_id="456",
            url="https://facebook.com/marketplace/listings/123",
        )
        with pytest.raises(AttributeError):
            result.listing_id = "999"

    def test_result_fields(self):
        """Result has correct fields."""
        result = FacebookMarketplaceListingResult(
            listing_id="123",
            product_id="456",
            url="https://facebook.com/marketplace/listings/123",
        )
        assert result.listing_id == "123"
        assert result.product_id == "456"
        assert "marketplace" in result.url
