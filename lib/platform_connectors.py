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


# Registry of all platform connectors
PLATFORMS = {
    "etsy": EtsyConnector,
    "depop": DepopConnector,
    "shopify": ShopifyConnector,
    "woocommerce": WooCommerceConnector,
    "mercari": MercariConnector,
    "poshmark": PoshmarkConnector,
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
