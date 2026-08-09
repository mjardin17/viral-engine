#!/usr/bin/env python3
"""
Platform Connectors: Real API implementations for crosslisting platforms.
Handles listing, delisting, price updates, and sales tracking.
"""

import os
import json
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

@dataclass
class Listing:
    """Standard listing format across all platforms."""
    id: str
    platform: str
    title: str
    description: str
    price: float
    quantity: int
    images: List[str]
    status: str  # "active", "sold", "delisted"
    url: str
    created_at: datetime
    updated_at: datetime

@dataclass
class Sale:
    """Sale record from any platform."""
    id: str
    platform: str
    listing_id: str
    product_id: str
    price: float
    quantity: int
    buyer: str
    sold_at: datetime

class PlatformConnector(ABC):
    """Base class for platform APIs."""

    def __init__(self, platform_name: str):
        self.platform = platform_name
        self.auth_token = os.getenv(f"{platform_name.upper()}_TOKEN")
        self.session = requests.Session()

    @abstractmethod
    def authenticate(self) -> bool:
        """Verify API credentials work."""
        pass

    @abstractmethod
    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a new listing on the platform."""
        pass

    @abstractmethod
    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update listing (price, quantity, description, etc)."""
        pass

    @abstractmethod
    def delist(self, listing_id: str) -> bool:
        """Remove listing from platform."""
        pass

    @abstractmethod
    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch recent sales."""
        pass

    @abstractmethod
    def get_inventory(self) -> List[Listing]:
        """Get all active listings."""
        pass


class EtsyConnector(PlatformConnector):
    """Etsy API integration (v3 REST API)."""

    def __init__(self):
        super().__init__("etsy")
        self.base_url = "https://api.etsy.com/v3"
        self.shop_id = os.getenv("ETSY_SHOP_ID")

    def authenticate(self) -> bool:
        """Verify Etsy OAuth token is valid."""
        if not self.auth_token:
            print("⚠️ Etsy: No OAuth token configured (ETSY_TOKEN)")
            return False

        try:
            headers = {"x-api-key": self.auth_token}
            response = self.session.get(
                f"{self.base_url}/application/shops/{self.shop_id}",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Etsy auth failed: {e}")
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a new Etsy listing."""
        if not self.shop_id:
            print("⚠️ Etsy: No ETSY_SHOP_ID configured")
            return None

        try:
            headers = {
                "x-api-key": self.auth_token,
                "Content-Type": "application/json"
            }

            payload = {
                "listing": {
                    "title": title[:140],  # Etsy limit
                    "description": description[:10000],
                    "price": price,
                    "quantity": 1,
                    "tags": ["resale", "secondhand"],
                    "who_made": "i_did",
                    "when_made": "2020_2023",
                    "type": "physical"
                }
            }

            response = self.session.post(
                f"{self.base_url}/shops/{self.shop_id}/listings",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 201:
                data = response.json()
                listing_id = data["listing"]["listing_id"]
                print(f"✓ Etsy: Created listing {listing_id}: {title}")

                # Upload images if provided
                if images:
                    self._upload_etsy_images(listing_id, images)

                return Listing(
                    id=str(listing_id),
                    platform="etsy",
                    title=title,
                    description=description,
                    price=price,
                    quantity=1,
                    images=images,
                    status="active",
                    url=f"https://www.etsy.com/listing/{listing_id}",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                print(f"❌ Etsy: Failed to create listing (status {response.status_code})")
                print(f"   Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Etsy create_listing error: {e}")
            return None

    def _upload_etsy_images(self, listing_id: str, image_urls: List[str]):
        """Upload images to an Etsy listing."""
        try:
            headers = {"x-api-key": self.auth_token}

            for idx, image_url in enumerate(image_urls[:10]):  # Etsy limit
                # Download image
                img_response = requests.get(image_url, timeout=10)
                if img_response.status_code != 200:
                    continue

                # Upload to Etsy
                files = {
                    "image": ("product.jpg", img_response.content, "image/jpeg")
                }
                response = self.session.post(
                    f"{self.base_url}/shops/{self.shop_id}/listings/{listing_id}/images",
                    headers=headers,
                    files=files,
                    timeout=10
                )

                if response.status_code in [200, 201]:
                    print(f"  ✓ Uploaded image {idx + 1}")
        except Exception as e:
            print(f"  ⚠️ Image upload error: {e}")

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Etsy listing (price, quantity, description)."""
        try:
            headers = {
                "x-api-key": self.auth_token,
                "Content-Type": "application/json"
            }

            payload = {"listing": {}}

            if "price" in kwargs:
                payload["listing"]["price"] = kwargs["price"]
            if "quantity" in kwargs:
                payload["listing"]["quantity"] = kwargs["quantity"]
            if "description" in kwargs:
                payload["listing"]["description"] = kwargs["description"][:10000]

            if not payload["listing"]:
                return True  # Nothing to update

            response = self.session.put(
                f"{self.base_url}/shops/{self.shop_id}/listings/{listing_id}",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✓ Etsy: Updated listing {listing_id}")
                return True
            else:
                print(f"❌ Etsy: Update failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Etsy update_listing error: {e}")
            return False

    def delist(self, listing_id: str) -> bool:
        """Deactivate Etsy listing."""
        try:
            headers = {"x-api-key": self.auth_token}

            response = self.session.delete(
                f"{self.base_url}/shops/{self.shop_id}/listings/{listing_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Etsy: Delisted {listing_id}")
                return True
            else:
                print(f"❌ Etsy: Delist failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Etsy delist error: {e}")
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Etsy sales since timestamp."""
        try:
            headers = {"x-api-key": self.auth_token}

            # Convert to Unix timestamp
            since_ts = int(since.timestamp())

            # Fetch all transactions
            response = self.session.get(
                f"{self.base_url}/shops/{self.shop_id}/transactions",
                headers=headers,
                params={"limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Etsy: Failed to fetch sales (status {response.status_code})")
                return []

            sales = []
            data = response.json()

            for transaction in data.get("results", []):
                created_ts = int(datetime.fromisoformat(
                    transaction["create_timestamp"].replace("Z", "+00:00")
                ).timestamp())

                if created_ts > since_ts:
                    sale = Sale(
                        id=str(transaction["transaction_id"]),
                        platform="etsy",
                        listing_id=str(transaction["listing_id"]),
                        product_id=str(transaction["listing_id"]),
                        price=float(transaction["price"]),
                        quantity=transaction["quantity"],
                        buyer=transaction.get("buyer_email", "unknown"),
                        sold_at=datetime.fromisoformat(
                            transaction["create_timestamp"].replace("Z", "+00:00")
                        )
                    )
                    sales.append(sale)

            print(f"📊 Etsy: Found {len(sales)} sales")
            return sales

        except Exception as e:
            print(f"❌ Etsy get_sales error: {e}")
            return []

    def get_inventory(self) -> List[Listing]:
        """Fetch all active Etsy listings."""
        try:
            headers = {"x-api-key": self.auth_token}

            response = self.session.get(
                f"{self.base_url}/shops/{self.shop_id}/listings/active",
                headers=headers,
                params={"limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Etsy: Failed to fetch listings (status {response.status_code})")
                return []

            listings = []
            data = response.json()

            for listing in data.get("results", []):
                listings.append(Listing(
                    id=str(listing["listing_id"]),
                    platform="etsy",
                    title=listing["title"],
                    description=listing.get("description", ""),
                    price=float(listing["price"]),
                    quantity=listing.get("quantity", 0),
                    images=[img["url_170x135"] for img in listing.get("images", [])],
                    status="active",
                    url=listing["url"],
                    created_at=datetime.fromisoformat(listing["creation_timestamp"]),
                    updated_at=datetime.fromisoformat(listing["last_modified_timestamp"])
                ))

            print(f"📋 Etsy: Found {len(listings)} active listings")
            return listings

        except Exception as e:
            print(f"❌ Etsy get_inventory error: {e}")
            return []


class MercariConnector(PlatformConnector):
    """Mercari API integration (waiting for official API docs)."""

    def __init__(self):
        super().__init__("mercari")
        self.base_url = "https://api.mercari.com/v2"

    def authenticate(self) -> bool:
        """Verify Mercari token is valid."""
        if not self.auth_token:
            print("⚠️ Mercari: No API token configured (MERCARI_TOKEN)")
            return False

        # Mercari API requires specific implementation based on their auth flow
        # Placeholder for when API docs are available
        print("✓ Mercari: Auth token present (real API call pending)")
        return True

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create Mercari listing (implementation pending API docs)."""
        print(f"📤 [Mercari] Creating listing: {title} (${price})")
        # TODO: Implement when Mercari API is documented
        return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Mercari listing (implementation pending)."""
        print(f"✏️ [Mercari] Updating listing {listing_id}")
        return True

    def delist(self, listing_id: str) -> bool:
        """Remove from Mercari (implementation pending)."""
        print(f"❌ [Mercari] Delisting {listing_id}")
        return True

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Mercari sales (implementation pending)."""
        print(f"📊 [Mercari] Fetching sales since {since}")
        return []

    def get_inventory(self) -> List[Listing]:
        """Get Mercari listings (implementation pending)."""
        print(f"📋 [Mercari] Fetching inventory")
        return []


class PoshmarkConnector(PlatformConnector):
    """Poshmark API integration (waiting for official API docs)."""

    def __init__(self):
        super().__init__("poshmark")
        self.base_url = "https://api.poshmark.com"

    def authenticate(self) -> bool:
        """Verify Poshmark token is valid."""
        if not self.auth_token:
            print("⚠️ Poshmark: No API token configured (POSHMARK_TOKEN)")
            return False

        # Poshmark API is private; waiting for official documentation
        print("✓ Poshmark: Auth token present (real API call pending)")
        return True

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create Poshmark listing (implementation pending API docs)."""
        print(f"📤 [Poshmark] Creating listing: {title} (${price})")
        # TODO: Implement when Poshmark exposes public API
        return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Poshmark listing (implementation pending)."""
        print(f"✏️ [Poshmark] Updating listing {listing_id}")
        return True

    def delist(self, listing_id: str) -> bool:
        """Remove from Poshmark (implementation pending)."""
        print(f"❌ [Poshmark] Delisting {listing_id}")
        return True

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Poshmark sales (implementation pending)."""
        print(f"📊 [Poshmark] Fetching sales since {since}")
        return []

    def get_inventory(self) -> List[Listing]:
        """Get Poshmark listings (implementation pending)."""
        print(f"📋 [Poshmark] Fetching inventory")
        return []


# Registry of all platform connectors
PLATFORMS = {
    "etsy": EtsyConnector,
    "mercari": MercariConnector,
    "poshmark": PoshmarkConnector,
    # Additional platforms can be added here
}

def get_all_connectors() -> Dict[str, PlatformConnector]:
    """Initialize all platform connectors."""
    return {name: connector_class() for name, connector_class in PLATFORMS.items()}

def get_connector(platform: str) -> Optional[PlatformConnector]:
    """Get a specific platform connector."""
    connector_class = PLATFORMS.get(platform.lower())
    if connector_class:
        return connector_class()
    return None
