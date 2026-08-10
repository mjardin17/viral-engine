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


class DepopConnector(PlatformConnector):
    """Depop API integration."""

    def __init__(self):
        super().__init__("depop")
        self.base_url = "https://www.depop.com/api"

    def authenticate(self) -> bool:
        """Verify Depop API token is valid."""
        if not self.auth_token:
            print("⚠️ Depop: No API token configured (DEPOP_TOKEN)")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(
                f"{self.base_url}/v1/user/profile",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Depop auth failed: {e}")
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a Depop listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "title": title[:50],  # Depop limit
                "description": description[:2000],
                "price": int(price * 100),  # Depop uses cents
                "currency": "USD",
                "category": "fashion",
                "photos": images[:8]  # Depop limit
            }

            response = self.session.post(
                f"{self.base_url}/v1/listings",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                data = response.json()
                listing_id = data.get("id")
                print(f"✓ Depop: Created listing {listing_id}: {title}")

                return Listing(
                    id=str(listing_id),
                    platform="depop",
                    title=title,
                    description=description,
                    price=price,
                    quantity=1,
                    images=images,
                    status="active",
                    url=f"https://www.depop.com/products/{listing_id}",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                print(f"❌ Depop: Failed to create listing (status {response.status_code})")
                return None

        except Exception as e:
            print(f"❌ Depop create_listing error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Depop listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {}
            if "price" in kwargs:
                payload["price"] = int(kwargs["price"] * 100)  # Convert to cents
            if "description" in kwargs:
                payload["description"] = kwargs["description"][:2000]

            if not payload:
                return True

            response = self.session.patch(
                f"{self.base_url}/v1/listings/{listing_id}",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Depop: Updated listing {listing_id}")
                return True
            else:
                print(f"❌ Depop: Update failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Depop update_listing error: {e}")
            return False

    def delist(self, listing_id: str) -> bool:
        """Deactivate Depop listing."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.delete(
                f"{self.base_url}/v1/listings/{listing_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Depop: Delisted {listing_id}")
                return True
            else:
                print(f"❌ Depop: Delist failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Depop delist error: {e}")
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Depop sales since timestamp."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/v1/sales",
                headers=headers,
                params={"limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Depop: Failed to fetch sales (status {response.status_code})")
                return []

            sales = []
            data = response.json()

            for sale in data.get("results", []):
                created_at = datetime.fromisoformat(sale["created_at"])
                if created_at > since:
                    sales.append(Sale(
                        id=str(sale["id"]),
                        platform="depop",
                        listing_id=str(sale["listing_id"]),
                        product_id=str(sale["listing_id"]),
                        price=sale["price"] / 100,  # Convert from cents
                        quantity=1,
                        buyer=sale.get("buyer_username", "unknown"),
                        sold_at=created_at
                    ))

            print(f"📊 Depop: Found {len(sales)} sales")
            return sales

        except Exception as e:
            print(f"❌ Depop get_sales error: {e}")
            return []

    def get_inventory(self) -> List[Listing]:
        """Fetch all active Depop listings."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/v1/listings?status=active",
                headers=headers,
                params={"limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Depop: Failed to fetch listings (status {response.status_code})")
                return []

            listings = []
            data = response.json()

            for listing in data.get("results", []):
                listings.append(Listing(
                    id=str(listing["id"]),
                    platform="depop",
                    title=listing["title"],
                    description=listing.get("description", ""),
                    price=listing["price"] / 100,  # Convert from cents
                    quantity=1 if listing.get("status") == "active" else 0,
                    images=[img["url"] for img in listing.get("images", [])],
                    status="active",
                    url=f"https://www.depop.com/products/{listing['id']}",
                    created_at=datetime.fromisoformat(listing["created_at"]),
                    updated_at=datetime.fromisoformat(listing["updated_at"])
                ))

            print(f"📋 Depop: Found {len(listings)} active listings")
            return listings

        except Exception as e:
            print(f"❌ Depop get_inventory error: {e}")
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

        print("✓ Mercari: Auth token present (real API call pending)")
        return True

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create Mercari listing (implementation pending API docs)."""
        print(f"📤 [Mercari] Creating listing: {title} (${price})")
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


class ShopifyConnector(PlatformConnector):
    """Shopify REST API integration."""

    def __init__(self):
        super().__init__("shopify")
        self.store_name = os.getenv("SHOPIFY_STORE_NAME")  # e.g., my-store.myshopify.com
        self.base_url = f"https://{self.store_name}/admin/api/2024-01/products.json"

    def authenticate(self) -> bool:
        """Verify Shopify API token is valid."""
        if not self.auth_token or not self.store_name:
            print("⚠️ Shopify: No API token or store name configured (SHOPIFY_TOKEN, SHOPIFY_STORE_NAME)")
            return False

        try:
            headers = {"X-Shopify-Access-Token": self.auth_token}
            response = self.session.get(
                f"https://{self.store_name}/admin/api/2024-01/shop.json",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Shopify auth failed: {e}")
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a Shopify product."""
        try:
            headers = {
                "X-Shopify-Access-Token": self.auth_token,
                "Content-Type": "application/json"
            }

            payload = {
                "product": {
                    "title": title,
                    "body_html": description,
                    "vendor": "Empire OS",
                    "product_type": "Resale",
                    "variants": [{
                        "price": price,
                        "requires_shipping": True
                    }],
                    "images": [{"src": img} for img in images[:8]]
                }
            }

            response = self.session.post(
                f"https://{self.store_name}/admin/api/2024-01/products.json",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                data = response.json()
                product_id = data["product"]["id"]
                print(f"✓ Shopify: Created product {product_id}: {title}")

                return Listing(
                    id=str(product_id),
                    platform="shopify",
                    title=title,
                    description=description,
                    price=price,
                    quantity=1,
                    images=images,
                    status="active",
                    url=f"https://{self.store_name}/products/{title.lower().replace(' ', '-')}",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                print(f"❌ Shopify: Failed to create product (status {response.status_code})")
                return None

        except Exception as e:
            print(f"❌ Shopify create_listing error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Shopify product."""
        try:
            headers = {
                "X-Shopify-Access-Token": self.auth_token,
                "Content-Type": "application/json"
            }

            payload = {"product": {}}

            if "price" in kwargs:
                payload["product"]["variants"] = [{"price": kwargs["price"]}]
            if "description" in kwargs:
                payload["product"]["body_html"] = kwargs["description"]
            if "title" in kwargs:
                payload["product"]["title"] = kwargs["title"]

            if len(payload["product"]) == 0:
                return True

            response = self.session.put(
                f"https://{self.store_name}/admin/api/2024-01/products/{listing_id}.json",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Shopify: Updated product {listing_id}")
                return True
            else:
                print(f"❌ Shopify: Update failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Shopify update_listing error: {e}")
            return False

    def delist(self, listing_id: str) -> bool:
        """Delete Shopify product."""
        try:
            headers = {"X-Shopify-Access-Token": self.auth_token}

            response = self.session.delete(
                f"https://{self.store_name}/admin/api/2024-01/products/{listing_id}.json",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Shopify: Deleted product {listing_id}")
                return True
            else:
                print(f"❌ Shopify: Delete failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Shopify delist error: {e}")
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Shopify orders since timestamp."""
        try:
            headers = {"X-Shopify-Access-Token": self.auth_token}

            response = self.session.get(
                f"https://{self.store_name}/admin/api/2024-01/orders.json",
                headers=headers,
                params={"limit": 100, "status": "any"},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Shopify: Failed to fetch orders (status {response.status_code})")
                return []

            sales = []
            data = response.json()

            for order in data.get("orders", []):
                created_at = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
                if created_at > since and order["financial_status"] == "paid":
                    for line_item in order.get("line_items", []):
                        sales.append(Sale(
                            id=str(order["id"]),
                            platform="shopify",
                            listing_id=str(line_item["product_id"]),
                            product_id=str(line_item["product_id"]),
                            price=float(line_item["price"]),
                            quantity=line_item["quantity"],
                            buyer=order["customer"].get("email", "unknown") if order.get("customer") else "unknown",
                            sold_at=created_at
                        ))

            print(f"📊 Shopify: Found {len(sales)} sales")
            return sales

        except Exception as e:
            print(f"❌ Shopify get_sales error: {e}")
            return []

    def get_inventory(self) -> List[Listing]:
        """Fetch all Shopify products."""
        try:
            headers = {"X-Shopify-Access-Token": self.auth_token}

            response = self.session.get(
                f"https://{self.store_name}/admin/api/2024-01/products.json",
                headers=headers,
                params={"limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Shopify: Failed to fetch products (status {response.status_code})")
                return []

            listings = []
            data = response.json()

            for product in data.get("products", []):
                variant = product["variants"][0] if product.get("variants") else {}
                listings.append(Listing(
                    id=str(product["id"]),
                    platform="shopify",
                    title=product["title"],
                    description=product.get("body_html", ""),
                    price=float(variant.get("price", 0)),
                    quantity=variant.get("inventory_quantity", 0),
                    images=[img["src"] for img in product.get("images", [])],
                    status="active",
                    url=f"https://{self.store_name}/products/{product['handle']}",
                    created_at=datetime.fromisoformat(product["created_at"]),
                    updated_at=datetime.fromisoformat(product["updated_at"])
                ))

            print(f"📋 Shopify: Found {len(listings)} products")
            return listings

        except Exception as e:
            print(f"❌ Shopify get_inventory error: {e}")
            return []


class WooCommerceConnector(PlatformConnector):
    """WooCommerce REST API integration."""

    def __init__(self):
        super().__init__("woocommerce")
        self.store_url = os.getenv("WOOCOMMERCE_URL")  # e.g., https://mystore.com
        self.key = os.getenv("WOOCOMMERCE_KEY")
        self.secret = os.getenv("WOOCOMMERCE_SECRET")
        self.base_url = f"{self.store_url}/wp-json/wc/v3"

    def authenticate(self) -> bool:
        """Verify WooCommerce credentials are valid."""
        if not self.store_url or not self.key or not self.secret:
            print("⚠️ WooCommerce: Missing credentials (WOOCOMMERCE_URL, WOOCOMMERCE_KEY, WOOCOMMERCE_SECRET)")
            return False

        try:
            response = self.session.get(
                f"{self.base_url}/system_status",
                auth=(self.key, self.secret),
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ WooCommerce auth failed: {e}")
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a WooCommerce product."""
        try:
            payload = {
                "name": title,
                "description": description,
                "price": str(price),
                "regular_price": str(price),
                "images": [{"src": img} for img in images],
                "type": "simple",
                "status": "publish"
            }

            response = self.session.post(
                f"{self.base_url}/products",
                auth=(self.key, self.secret),
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                data = response.json()
                product_id = data["id"]
                print(f"✓ WooCommerce: Created product {product_id}: {title}")

                return Listing(
                    id=str(product_id),
                    platform="woocommerce",
                    title=title,
                    description=description,
                    price=price,
                    quantity=1,
                    images=images,
                    status="active",
                    url=data.get("permalink", ""),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                print(f"❌ WooCommerce: Failed to create product (status {response.status_code})")
                return None

        except Exception as e:
            print(f"❌ WooCommerce create_listing error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update WooCommerce product."""
        try:
            payload = {}

            if "price" in kwargs:
                payload["price"] = str(kwargs["price"])
                payload["regular_price"] = str(kwargs["price"])
            if "description" in kwargs:
                payload["description"] = kwargs["description"]
            if "title" in kwargs:
                payload["name"] = kwargs["title"]

            if not payload:
                return True

            response = self.session.post(
                f"{self.base_url}/products/{listing_id}",
                auth=(self.key, self.secret),
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ WooCommerce: Updated product {listing_id}")
                return True
            else:
                print(f"❌ WooCommerce: Update failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ WooCommerce update_listing error: {e}")
            return False

    def delist(self, listing_id: str) -> bool:
        """Delete WooCommerce product."""
        try:
            response = self.session.delete(
                f"{self.base_url}/products/{listing_id}",
                auth=(self.key, self.secret),
                params={"force": True},
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ WooCommerce: Deleted product {listing_id}")
                return True
            else:
                print(f"❌ WooCommerce: Delete failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ WooCommerce delist error: {e}")
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch WooCommerce orders since timestamp."""
        try:
            since_str = since.isoformat()

            response = self.session.get(
                f"{self.base_url}/orders",
                auth=(self.key, self.secret),
                params={"after": since_str, "per_page": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ WooCommerce: Failed to fetch orders (status {response.status_code})")
                return []

            sales = []
            data = response.json()

            for order in data:
                if order["status"] in ["completed", "processing"]:
                    for line_item in order.get("line_items", []):
                        sales.append(Sale(
                            id=str(order["id"]),
                            platform="woocommerce",
                            listing_id=str(line_item["product_id"]),
                            product_id=str(line_item["product_id"]),
                            price=float(line_item["price"]),
                            quantity=line_item["quantity"],
                            buyer=order["billing"]["email"],
                            sold_at=datetime.fromisoformat(order["date_created"])
                        ))

            print(f"📊 WooCommerce: Found {len(sales)} orders")
            return sales

        except Exception as e:
            print(f"❌ WooCommerce get_sales error: {e}")
            return []

    def get_inventory(self) -> List[Listing]:
        """Fetch all WooCommerce products."""
        try:
            response = self.session.get(
                f"{self.base_url}/products",
                auth=(self.key, self.secret),
                params={"per_page": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ WooCommerce: Failed to fetch products (status {response.status_code})")
                return []

            listings = []
            data = response.json()

            for product in data:
                listings.append(Listing(
                    id=str(product["id"]),
                    platform="woocommerce",
                    title=product["name"],
                    description=product.get("description", ""),
                    price=float(product.get("price", 0)),
                    quantity=product.get("stock_quantity", 0) or 0,
                    images=[img["src"] for img in product.get("images", [])],
                    status="active" if product["status"] == "publish" else "inactive",
                    url=product.get("permalink", ""),
                    created_at=datetime.fromisoformat(product["date_created"]),
                    updated_at=datetime.fromisoformat(product["date_modified"])
                ))

            print(f"📋 WooCommerce: Found {len(listings)} products")
            return listings

        except Exception as e:
            print(f"❌ WooCommerce get_inventory error: {e}")
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

        print("✓ Poshmark: Auth token present (real API call pending)")
        return True

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create Poshmark listing (implementation pending API docs)."""
        print(f"📤 [Poshmark] Creating listing: {title} (${price})")
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


class GrailedConnector(PlatformConnector):
    """Grailed API integration (streetwear marketplace)."""

    def __init__(self):
        super().__init__("grailed")
        self.base_url = "https://api.grailed.com/api/v2"

    def authenticate(self) -> bool:
        """Verify Grailed API token is valid."""
        if not self.auth_token:
            print("⚠️ Grailed: No API token configured (GRAILED_TOKEN)")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(
                f"{self.base_url}/me",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Grailed auth failed: {e}")
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a Grailed listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "listing": {
                    "title": title[:100],
                    "description": description,
                    "price_cents": int(price * 100),
                    "category": "tops",
                    "size": "One Size",
                    "condition": "New",
                    "photos": [{"url": img} for img in images[:8]]
                }
            }

            response = self.session.post(
                f"{self.base_url}/listings",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                data = response.json()
                listing_id = data.get("listing", {}).get("id")
                print(f"✓ Grailed: Created listing {listing_id}: {title}")

                return Listing(
                    id=str(listing_id),
                    platform="grailed",
                    title=title,
                    description=description,
                    price=price,
                    quantity=1,
                    images=images,
                    status="active",
                    url=f"https://www.grailed.com/listings/{listing_id}",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                print(f"❌ Grailed: Failed to create listing (status {response.status_code})")
                return None

        except Exception as e:
            print(f"❌ Grailed create_listing error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Grailed listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {"listing": {}}

            if "price" in kwargs:
                payload["listing"]["price_cents"] = int(kwargs["price"] * 100)
            if "description" in kwargs:
                payload["listing"]["description"] = kwargs["description"]

            if len(payload["listing"]) == 0:
                return True

            response = self.session.put(
                f"{self.base_url}/listings/{listing_id}",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Grailed: Updated listing {listing_id}")
                return True
            else:
                print(f"❌ Grailed: Update failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Grailed update_listing error: {e}")
            return False

    def delist(self, listing_id: str) -> bool:
        """Delete Grailed listing."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.delete(
                f"{self.base_url}/listings/{listing_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Grailed: Delisted {listing_id}")
                return True
            else:
                print(f"❌ Grailed: Delist failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Grailed delist error: {e}")
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Grailed sales since timestamp."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/me/sales",
                headers=headers,
                params={"limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Grailed: Failed to fetch sales (status {response.status_code})")
                return []

            sales = []
            data = response.json()

            for sale in data.get("sales", []):
                created_at = datetime.fromisoformat(sale.get("created_at", "").replace("Z", "+00:00"))
                if created_at > since:
                    sales.append(Sale(
                        id=str(sale["id"]),
                        platform="grailed",
                        listing_id=str(sale.get("listing_id")),
                        product_id=str(sale.get("listing_id")),
                        price=sale.get("price_cents", 0) / 100,
                        quantity=1,
                        buyer=sale.get("buyer", {}).get("username", "unknown"),
                        sold_at=created_at
                    ))

            print(f"📊 Grailed: Found {len(sales)} sales")
            return sales

        except Exception as e:
            print(f"❌ Grailed get_sales error: {e}")
            return []

    def get_inventory(self) -> List[Listing]:
        """Fetch all Grailed listings."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/me/listings",
                headers=headers,
                params={"limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Grailed: Failed to fetch listings (status {response.status_code})")
                return []

            listings = []
            data = response.json()

            for listing in data.get("listings", []):
                listings.append(Listing(
                    id=str(listing["id"]),
                    platform="grailed",
                    title=listing["title"],
                    description=listing.get("description", ""),
                    price=listing.get("price_cents", 0) / 100,
                    quantity=1 if listing.get("status") == "active" else 0,
                    images=[p.get("url") for p in listing.get("photos", [])],
                    status="active" if listing.get("status") == "active" else "inactive",
                    url=f"https://www.grailed.com/listings/{listing['id']}",
                    created_at=datetime.fromisoformat(listing.get("created_at", "").replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(listing.get("updated_at", "").replace("Z", "+00:00"))
                ))

            print(f"📋 Grailed: Found {len(listings)} listings")
            return listings

        except Exception as e:
            print(f"❌ Grailed get_inventory error: {e}")
            return []


class VintedConnector(PlatformConnector):
    """Vinted API integration (fashion resale)."""

    def __init__(self):
        super().__init__("vinted")
        self.base_url = "https://www.vinted.com/api/v2"

    def authenticate(self) -> bool:
        """Verify Vinted API token is valid."""
        if not self.auth_token:
            print("⚠️ Vinted: No API token configured (VINTED_TOKEN)")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(
                f"{self.base_url}/user",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Vinted auth failed: {e}")
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a Vinted listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "item": {
                    "title": title,
                    "description": description,
                    "price": price,
                    "currency": "USD",
                    "size_id": 0,
                    "brand_id": 0,
                    "photo_ids": list(range(len(images[:10])))
                }
            }

            response = self.session.post(
                f"{self.base_url}/items",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                data = response.json()
                item_id = data.get("item", {}).get("id")
                print(f"✓ Vinted: Created listing {item_id}: {title}")

                return Listing(
                    id=str(item_id),
                    platform="vinted",
                    title=title,
                    description=description,
                    price=price,
                    quantity=1,
                    images=images,
                    status="active",
                    url=f"https://www.vinted.com/items/{item_id}",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                print(f"❌ Vinted: Failed to create listing (status {response.status_code})")
                return None

        except Exception as e:
            print(f"❌ Vinted create_listing error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Vinted listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {"item": {}}

            if "price" in kwargs:
                payload["item"]["price"] = kwargs["price"]
            if "description" in kwargs:
                payload["item"]["description"] = kwargs["description"]

            if len(payload["item"]) == 0:
                return True

            response = self.session.put(
                f"{self.base_url}/items/{listing_id}",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Vinted: Updated listing {listing_id}")
                return True
            else:
                print(f"❌ Vinted: Update failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Vinted update_listing error: {e}")
            return False

    def delist(self, listing_id: str) -> bool:
        """Delete Vinted listing."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.delete(
                f"{self.base_url}/items/{listing_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Vinted: Delisted {listing_id}")
                return True
            else:
                print(f"❌ Vinted: Delist failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Vinted delist error: {e}")
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Vinted sales since timestamp."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/transactions",
                headers=headers,
                params={"status": "completed", "limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Vinted: Failed to fetch sales (status {response.status_code})")
                return []

            sales = []
            data = response.json()

            for tx in data.get("transactions", []):
                created_at = datetime.fromisoformat(tx.get("created_at", "").replace("Z", "+00:00"))
                if created_at > since:
                    sales.append(Sale(
                        id=str(tx["id"]),
                        platform="vinted",
                        listing_id=str(tx.get("item_id")),
                        product_id=str(tx.get("item_id")),
                        price=float(tx.get("price", 0)),
                        quantity=1,
                        buyer=tx.get("buyer", {}).get("login", "unknown"),
                        sold_at=created_at
                    ))

            print(f"📊 Vinted: Found {len(sales)} sales")
            return sales

        except Exception as e:
            print(f"❌ Vinted get_sales error: {e}")
            return []

    def get_inventory(self) -> List[Listing]:
        """Fetch all Vinted listings."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/items",
                headers=headers,
                params={"status": "active", "limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Vinted: Failed to fetch listings (status {response.status_code})")
                return []

            listings = []
            data = response.json()

            for item in data.get("items", []):
                listings.append(Listing(
                    id=str(item["id"]),
                    platform="vinted",
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    price=float(item.get("price", 0)),
                    quantity=1 if item.get("status") == "active" else 0,
                    images=[p.get("url") for p in item.get("photos", [])],
                    status="active" if item.get("status") == "active" else "inactive",
                    url=f"https://www.vinted.com/items/{item['id']}",
                    created_at=datetime.fromisoformat(item.get("created_at", "").replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(item.get("updated_at", "").replace("Z", "+00:00"))
                ))

            print(f"📋 Vinted: Found {len(listings)} listings")
            return listings

        except Exception as e:
            print(f"❌ Vinted get_inventory error: {e}")
            return []


class VestiaireConnector(PlatformConnector):
    """Vestiaire Collective API integration (luxury resale)."""

    def __init__(self):
        super().__init__("vestiaire")
        self.base_url = "https://api.vestiaire.com/v2"

    def authenticate(self) -> bool:
        """Verify Vestiaire Collective API token is valid."""
        if not self.auth_token:
            print("⚠️ Vestiaire: No API token configured (VESTIAIRE_TOKEN)")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(
                f"{self.base_url}/me",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Vestiaire auth failed: {e}")
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        """Create a Vestiaire Collective listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "product": {
                    "name": title,
                    "description": description,
                    "price": int(price * 100),
                    "currency": "USD",
                    "condition": "Never Worn",
                    "photos": [{"url": img} for img in images[:10]]
                }
            }

            response = self.session.post(
                f"{self.base_url}/products",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                data = response.json()
                product_id = data.get("product", {}).get("id")
                print(f"✓ Vestiaire: Created listing {product_id}: {title}")

                return Listing(
                    id=str(product_id),
                    platform="vestiaire",
                    title=title,
                    description=description,
                    price=price,
                    quantity=1,
                    images=images,
                    status="active",
                    url=f"https://www.vestiaire.com/p/{product_id}",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                print(f"❌ Vestiaire: Failed to create listing (status {response.status_code})")
                return None

        except Exception as e:
            print(f"❌ Vestiaire create_listing error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        """Update Vestiaire Collective listing."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }

            payload = {"product": {}}

            if "price" in kwargs:
                payload["product"]["price"] = int(kwargs["price"] * 100)
            if "description" in kwargs:
                payload["product"]["description"] = kwargs["description"]

            if len(payload["product"]) == 0:
                return True

            response = self.session.put(
                f"{self.base_url}/products/{listing_id}",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Vestiaire: Updated listing {listing_id}")
                return True
            else:
                print(f"❌ Vestiaire: Update failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Vestiaire update_listing error: {e}")
            return False

    def delist(self, listing_id: str) -> bool:
        """Delete Vestiaire Collective listing."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.delete(
                f"{self.base_url}/products/{listing_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code in [200, 204]:
                print(f"✓ Vestiaire: Delisted {listing_id}")
                return True
            else:
                print(f"❌ Vestiaire: Delist failed (status {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ Vestiaire delist error: {e}")
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        """Fetch Vestiaire Collective sales since timestamp."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/orders",
                headers=headers,
                params={"status": "completed", "limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Vestiaire: Failed to fetch sales (status {response.status_code})")
                return []

            sales = []
            data = response.json()

            for order in data.get("orders", []):
                created_at = datetime.fromisoformat(order.get("created_at", "").replace("Z", "+00:00"))
                if created_at > since:
                    sales.append(Sale(
                        id=str(order["id"]),
                        platform="vestiaire",
                        listing_id=str(order.get("product_id")),
                        product_id=str(order.get("product_id")),
                        price=order.get("price", 0) / 100,
                        quantity=1,
                        buyer=order.get("buyer", {}).get("username", "unknown"),
                        sold_at=created_at
                    ))

            print(f"📊 Vestiaire: Found {len(sales)} sales")
            return sales

        except Exception as e:
            print(f"❌ Vestiaire get_sales error: {e}")
            return []

    def get_inventory(self) -> List[Listing]:
        """Fetch all Vestiaire Collective listings."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = self.session.get(
                f"{self.base_url}/products",
                headers=headers,
                params={"status": "active", "limit": 100},
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Vestiaire: Failed to fetch listings (status {response.status_code})")
                return []

            listings = []
            data = response.json()

            for product in data.get("products", []):
                listings.append(Listing(
                    id=str(product["id"]),
                    platform="vestiaire",
                    title=product.get("name", ""),
                    description=product.get("description", ""),
                    price=product.get("price", 0) / 100,
                    quantity=1 if product.get("status") == "active" else 0,
                    images=[p.get("url") for p in product.get("photos", [])],
                    status="active" if product.get("status") == "active" else "inactive",
                    url=f"https://www.vestiaire.com/p/{product['id']}",
                    created_at=datetime.fromisoformat(product.get("created_at", "").replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(product.get("updated_at", "").replace("Z", "+00:00"))
                ))

            print(f"📋 Vestiaire: Found {len(listings)} listings")
            return listings

        except Exception as e:
            print(f"❌ Vestiaire get_inventory error: {e}")
            return []


class EbayConnector(PlatformConnector):
    """eBay Trading API integration."""

    def __init__(self):
        super().__init__("ebay")
        self.base_url = "https://api.ebay.com/sell/inventory/v1"

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ eBay: No API token configured (EBAY_TOKEN)")
            return False
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/inventory_item", headers=headers, timeout=5)
            return response.status_code in [200, 400]
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            payload = {"title": title[:80], "description": description[:5000], "price": price, "images": images[:12]}
            response = self.session.post(f"{self.base_url}/inventory_item", headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                listing_id = response.json().get("id")
                print(f"✓ eBay: Created {listing_id}")
                return Listing(str(listing_id), "ebay", title, description, price, 1, images, "active", f"https://ebay.com/{listing_id}", datetime.now(), datetime.now())
            return None
        except Exception as e:
            print(f"❌ eBay error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            payload = {}
            if "price" in kwargs:
                payload["price"] = kwargs["price"]
            if not payload:
                return True
            response = self.session.put(f"{self.base_url}/inventory_item/{listing_id}", headers=headers, json=payload, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.delete(f"{self.base_url}/inventory_item/{listing_id}", headers=headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/orders", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            sales = []
            for order in response.json().get("orders", []):
                created_at = datetime.fromisoformat(order.get("created_at", "").replace("Z", "+00:00"))
                if created_at > since:
                    sales.append(Sale(str(order["id"]), "ebay", str(order.get("item_id")), str(order.get("item_id")), float(order.get("price", 0)), 1, order.get("buyer"), created_at))
            print(f"📊 eBay: Found {len(sales)} sales")
            return sales
        except:
            return []

    def get_inventory(self) -> List[Listing]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/inventory_item", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            listings = []
            for item in response.json().get("items", []):
                listings.append(Listing(str(item["id"]), "ebay", item.get("title", ""), item.get("description", ""), float(item.get("price", 0)), item.get("quantity", 0), item.get("images", []), "active", f"https://ebay.com/{item['id']}", datetime.now(), datetime.now()))
            print(f"📋 eBay: Found {len(listings)} listings")
            return listings
        except:
            return []


class FacebookMarketplaceConnector(PlatformConnector):
    """Facebook Marketplace API integration."""

    def __init__(self):
        super().__init__("facebook")
        self.base_url = "https://graph.facebook.com/v18.0"

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Facebook: No API token configured (FACEBOOK_TOKEN)")
            return False
        try:
            response = self.session.get(f"{self.base_url}/me", params={"access_token": self.auth_token}, timeout=5)
            return response.status_code == 200
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            payload = {"name": title, "description": description, "price": int(price * 100), "image_urls": images[:8]}
            response = self.session.post(f"{self.base_url}/me/marketplace_listings", data=payload, params={"access_token": self.auth_token}, timeout=10)
            if response.status_code in [200, 201]:
                listing_id = response.json().get("id")
                print(f"✓ Facebook: Created {listing_id}")
                return Listing(str(listing_id), "facebook", title, description, price, 1, images, "active", f"https://facebook.com/marketplace/listings/{listing_id}", datetime.now(), datetime.now())
            return None
        except Exception as e:
            print(f"❌ Facebook error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            payload = {}
            if "price" in kwargs:
                payload["price"] = int(kwargs["price"] * 100)
            if not payload:
                return True
            response = self.session.post(f"{self.base_url}/{listing_id}", data=payload, params={"access_token": self.auth_token}, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            response = self.session.delete(f"{self.base_url}/{listing_id}", params={"access_token": self.auth_token}, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        return []

    def get_inventory(self) -> List[Listing]:
        try:
            response = self.session.get(f"{self.base_url}/me/marketplace_listings", params={"access_token": self.auth_token}, timeout=10)
            if response.status_code != 200:
                return []
            listings = [Listing(str(item["id"]), "facebook", item.get("name", ""), item.get("description", ""), float(item.get("price", 0) / 100), 1, item.get("images", []), "active", f"https://facebook.com/marketplace/listings/{item['id']}", datetime.now(), datetime.now()) for item in response.json().get("listings", [])]
            print(f"📋 Facebook: Found {len(listings)} listings")
            return listings
        except:
            return []


class MercadoLibreConnector(PlatformConnector):
    """Mercado Libre API integration (Latin America)."""

    def __init__(self):
        super().__init__("mercadolibre")
        self.base_url = "https://api.mercadolibre.com"

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Mercado Libre: No API token configured (MERCADOLIBRE_TOKEN)")
            return False
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/users/me", headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            payload = {"title": title, "description": description, "price": price, "currency_id": "USD", "pictures": [{"url": img} for img in images[:8]]}
            response = self.session.post(f"{self.base_url}/items", headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                listing_id = response.json().get("id")
                print(f"✓ Mercado Libre: Created {listing_id}")
                return Listing(str(listing_id), "mercadolibre", title, description, price, 1, images, "active", f"https://mercadolibre.com.ar/p/{listing_id}", datetime.now(), datetime.now())
            return None
        except Exception as e:
            print(f"❌ Mercado Libre error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            payload = {}
            if "price" in kwargs:
                payload["price"] = kwargs["price"]
            if not payload:
                return True
            response = self.session.put(f"{self.base_url}/items/{listing_id}", headers=headers, json=payload, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.delete(f"{self.base_url}/items/{listing_id}", headers=headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/orders/search", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            return [Sale(str(order["id"]), "mercadolibre", str(order.get("item_id")), str(order.get("item_id")), float(order.get("price", 0)), 1, order.get("buyer"), datetime.fromisoformat(order.get("date_created", "").replace("Z", "+00:00"))) for order in response.json().get("orders", []) if datetime.fromisoformat(order.get("date_created", "").replace("Z", "+00:00")) > since]
        except:
            return []

    def get_inventory(self) -> List[Listing]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/users/me/listings", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            listings = [Listing(str(item["id"]), "mercadolibre", item.get("title", ""), "", float(item.get("price", 0)), item.get("available_quantity", 0), item.get("pictures", []), "active", f"https://mercadolibre.com.ar/p/{item['id']}", datetime.now(), datetime.now()) for item in response.json().get("results", [])]
            print(f"📋 Mercado Libre: Found {len(listings)} listings")
            return listings
        except:
            return []


class ReverbConnector(PlatformConnector):
    """Reverb.com API integration (music gear)."""

    def __init__(self):
        super().__init__("reverb")
        self.base_url = "https://api.reverb.com/api/own"

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Reverb: No API token configured (REVERB_TOKEN)")
            return False
        try:
            headers = {"Authorization": f"Token token={self.auth_token}"}
            response = self.session.get(f"{self.base_url}/profile", headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            headers = {"Authorization": f"Token token={self.auth_token}"}
            payload = {"listing": {"title": title, "description": description, "price": price, "photo_ids": list(range(len(images[:10])))}}
            response = self.session.post(f"{self.base_url}/listings", headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                listing_id = response.json().get("listing", {}).get("id")
                print(f"✓ Reverb: Created {listing_id}")
                return Listing(str(listing_id), "reverb", title, description, price, 1, images, "active", f"https://reverb.com/item/{listing_id}", datetime.now(), datetime.now())
            return None
        except Exception as e:
            print(f"❌ Reverb error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            headers = {"Authorization": f"Token token={self.auth_token}"}
            payload = {"listing": {}}
            if "price" in kwargs:
                payload["listing"]["price"] = kwargs["price"]
            if not payload["listing"]:
                return True
            response = self.session.put(f"{self.base_url}/listings/{listing_id}", headers=headers, json=payload, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            headers = {"Authorization": f"Token token={self.auth_token}"}
            response = self.session.delete(f"{self.base_url}/listings/{listing_id}", headers=headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        try:
            headers = {"Authorization": f"Token token={self.auth_token}"}
            response = self.session.get(f"{self.base_url}/sales", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            return [Sale(str(sale["id"]), "reverb", str(sale.get("listing_id")), str(sale.get("listing_id")), float(sale.get("price", 0)), 1, sale.get("buyer"), datetime.fromisoformat(sale.get("created_at", "").replace("Z", "+00:00"))) for sale in response.json().get("sales", []) if datetime.fromisoformat(sale.get("created_at", "").replace("Z", "+00:00")) > since]
        except:
            return []

    def get_inventory(self) -> List[Listing]:
        try:
            headers = {"Authorization": f"Token token={self.auth_token}"}
            response = self.session.get(f"{self.base_url}/listings", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            listings = [Listing(str(item["id"]), "reverb", item.get("title", ""), item.get("description", ""), float(item.get("price", 0)), 1, item.get("photos", []), "active", f"https://reverb.com/item/{item['id']}", datetime.now(), datetime.now()) for item in response.json().get("listings", [])]
            print(f"📋 Reverb: Found {len(listings)} listings")
            return listings
        except:
            return []


class RealRealConnector(PlatformConnector):
    """The RealReal API integration (luxury resale)."""

    def __init__(self):
        super().__init__("realreal")
        self.base_url = "https://api.therealreal.com/v1"

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ The RealReal: No API token configured (REALREAL_TOKEN)")
            return False
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/seller/profile", headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            payload = {"title": title, "description": description, "price": price, "photos": images[:10]}
            response = self.session.post(f"{self.base_url}/listings", headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                listing_id = response.json().get("id")
                print(f"✓ The RealReal: Created {listing_id}")
                return Listing(str(listing_id), "realreal", title, description, price, 1, images, "active", f"https://therealreal.com/products/{listing_id}", datetime.now(), datetime.now())
            return None
        except Exception as e:
            print(f"❌ The RealReal error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            payload = {}
            if "price" in kwargs:
                payload["price"] = kwargs["price"]
            if not payload:
                return True
            response = self.session.patch(f"{self.base_url}/listings/{listing_id}", headers=headers, json=payload, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.delete(f"{self.base_url}/listings/{listing_id}", headers=headers, timeout=10)
            return response.status_code in [200, 204]
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/sales", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            return [Sale(str(sale["id"]), "realreal", str(sale.get("listing_id")), str(sale.get("listing_id")), float(sale.get("price", 0)), 1, sale.get("buyer"), datetime.fromisoformat(sale.get("date", "").replace("Z", "+00:00"))) for sale in response.json().get("sales", []) if datetime.fromisoformat(sale.get("date", "").replace("Z", "+00:00")) > since]
        except:
            return []

    def get_inventory(self) -> List[Listing]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/listings", headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            listings = [Listing(str(item["id"]), "realreal", item.get("title", ""), item.get("description", ""), float(item.get("price", 0)), 1, item.get("photos", []), "active", f"https://therealreal.com/products/{item['id']}", datetime.now(), datetime.now()) for item in response.json().get("listings", [])]
            print(f"📋 The RealReal: Found {len(listings)} listings")
            return listings
        except:
            return []


# Try importing browser connectors
try:
    from lib.browser_connectors import BROWSER_CONNECTORS
    _browser_available = True
except ImportError:
    BROWSER_CONNECTORS = {}
    _browser_available = False

# Registry of all platform connectors
# Priority: Browser automation (no-API platforms) > REST APIs > Stubs
PLATFORMS = {
    # REST API connectors (full automation with API keys)
    "etsy": EtsyConnector,
    "shopify": ShopifyConnector,
    "woocommerce": WooCommerceConnector,
    "grailed": GrailedConnector,
    "vinted": VintedConnector,
    "vestiaire": VestiaireConnector,
    "ebay": EbayConnector,
    "facebook": FacebookMarketplaceConnector,
    "mercadolibre": MercadoLibreConnector,
    "reverb": ReverbConnector,
    "realreal": RealRealConnector,
}

# Add browser automation connectors if Playwright is available
if _browser_available:
    PLATFORMS.update(BROWSER_CONNECTORS)
    # Override stubs with browser versions
    PLATFORMS["depop"] = BROWSER_CONNECTORS.get("depop_web", DepopConnector)
    PLATFORMS["mercari"] = BROWSER_CONNECTORS.get("mercari_web", MercariConnector)
    PLATFORMS["poshmark"] = BROWSER_CONNECTORS.get("poshmark_web", PoshmarkConnector)
    PLATFORMS["whatnot"] = BROWSER_CONNECTORS.get("whatnot_web")
else:
    # Fallback to stubs if Playwright not available
    PLATFORMS["depop"] = DepopConnector
    PLATFORMS["mercari"] = MercariConnector
    PLATFORMS["poshmark"] = PoshmarkConnector

def get_all_connectors() -> Dict[str, PlatformConnector]:
    """Initialize all platform connectors."""
    return {name: connector_class() for name, connector_class in PLATFORMS.items()}

def get_connector(platform: str) -> Optional[PlatformConnector]:
    """Get a specific platform connector."""
    connector_class = PLATFORMS.get(platform.lower())
    if connector_class:
        return connector_class()
    return None
