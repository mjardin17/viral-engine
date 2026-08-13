#!/usr/bin/env python3
"""
eBay Inventory & Listing Management API
Full CRUD operations for eBay inventory items.
"""

import requests
import json
from typing import List, Dict, Optional
from datetime import datetime
from lib.ebay_oauth_handler import EbayOAuthHandler

class EbayInventoryConnector:
    """Manages eBay inventory and listings via REST API."""

    def __init__(self, oauth_handler: EbayOAuthHandler):
        self.oauth = oauth_handler
        self.base_url = "https://api.ebay.com/sell/inventory/v1" if not oauth_handler.use_sandbox else "https://api.sandbox.ebay.com/sell/inventory/v1"
        self.fulfillment_url = "https://api.ebay.com/sell/fulfillment/v1" if not oauth_handler.use_sandbox else "https://api.sandbox.ebay.com/sell/fulfillment/v1"

    def _get_headers(self) -> Dict:
        """Get headers with valid authorization token."""
        token = self.oauth.get_valid_token()
        if not token:
            raise Exception("No valid eBay token. Re-authenticate required.")

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def create_inventory_item(self, sku: str, product: Dict) -> Dict:
        """
        Create an inventory item (doesn't list it yet).

        Args:
            sku: Stock Keeping Unit (unique identifier)
            product: Product details (title, description, price, images, etc)
        """
        try:
            headers = self._get_headers()

            payload = {
                "availability": {
                    "shipToLocationAvailability": [
                        {
                            "quantity": product.get("quantity", 1),
                            "location": "DEFAULT"
                        }
                    ]
                },
                "condition": _map_to_ebay_condition(product.get("condition", "USED_GOOD")),
                "product": {
                    "title": product.get("name", "Product")[:80],
                    "description": product.get("description", "")[:10000],
                    "imageUrls": product.get("images", [])[:12],  # eBay max 12 images
                    "categories": [{"categoryId": product.get("category_id", "1")}]
                }
            }

            response = requests.post(
                f"{self.base_url}/inventory_item/{sku}",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()

            return {
                "status": "success",
                "sku": sku,
                "message": f"Inventory item created for SKU {sku}"
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e), "sku": sku}

    def create_listing(self, sku: str, listing_config: Dict) -> Dict:
        """
        Create an active eBay listing from inventory item.

        Args:
            sku: Stock Keeping Unit
            listing_config: Pricing, duration, shipping, etc
        """
        try:
            headers = self._get_headers()

            payload = {
                "listingDuration": listing_config.get("duration", "GTC"),  # Good-Till-Cancelled
                "listingPolicies": {
                    "paymentPolicyId": listing_config.get("payment_policy_id"),
                    "fulfillmentPolicyId": listing_config.get("fulfillment_policy_id"),
                    "returnPolicyId": listing_config.get("return_policy_id")
                },
                "pricingSummary": {
                    "price": {
                        "currency": "USD",
                        "value": str(listing_config.get("price", 0))
                    },
                    "minimumAdvertisedPrice": {
                        "currency": "USD",
                        "value": str(listing_config.get("map_price", 0))
                    } if listing_config.get("map_price") else None
                },
                "quantityLimitPerBuyer": listing_config.get("qty_per_buyer", 5),
                "taxSetting": listing_config.get("tax_setting")
            }

            response = requests.post(
                f"{self.base_url}/listing",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()

            listing_response = response.json()
            listing_id = listing_response.get("listingId")

            return {
                "status": "success",
                "listing_id": listing_id,
                "sku": sku,
                "url": f"https://ebay.com/itm/{listing_id}" if not self.oauth.use_sandbox else "https://sandbox.ebay.com"
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e), "sku": sku}

    def end_listing(self, listing_id: str, reason: str = "NotAvailable") -> Dict:
        """End (delist) an eBay listing."""
        try:
            headers = self._get_headers()

            payload = {"endingReason": reason}

            response = requests.post(
                f"{self.base_url}/listing/{listing_id}/end_sale",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()

            return {
                "status": "success",
                "listing_id": listing_id,
                "message": "Listing ended"
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

    def update_price(self, sku: str, new_price: float) -> Dict:
        """Update listing price for an inventory item."""
        try:
            headers = self._get_headers()

            payload = {
                "pricingSummary": {
                    "price": {
                        "currency": "USD",
                        "value": str(new_price)
                    }
                }
            }

            response = requests.patch(
                f"{self.base_url}/inventory_item/{sku}",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()

            return {
                "status": "success",
                "sku": sku,
                "new_price": new_price
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e), "sku": sku}

    def update_quantity(self, sku: str, new_quantity: int) -> Dict:
        """Update available quantity for an inventory item."""
        try:
            headers = self._get_headers()

            payload = {
                "availability": {
                    "shipToLocationAvailability": [
                        {
                            "quantity": new_quantity,
                            "location": "DEFAULT"
                        }
                    ]
                }
            }

            response = requests.patch(
                f"{self.base_url}/inventory_item/{sku}",
                headers=headers,
                json=payload,
                timeout=15
            )
            response.raise_for_status()

            return {
                "status": "success",
                "sku": sku,
                "new_quantity": new_quantity
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e), "sku": sku}

    def get_inventory_item(self, sku: str) -> Dict:
        """Fetch inventory item details."""
        try:
            headers = self._get_headers()

            response = requests.get(
                f"{self.base_url}/inventory_item/{sku}",
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            item = response.json()
            return {
                "status": "success",
                "item": item
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

    def get_orders(self, since: str = None, limit: int = 50) -> Dict:
        """
        Fetch recent orders.

        Args:
            since: ISO 8601 datetime to fetch orders after
            limit: Max orders to return (default 50)
        """
        try:
            headers = self._get_headers()

            params = {
                "limit": limit,
                "offset": 0
            }

            if since:
                params["filter"] = f"creationdate:[{since}..]"

            response = requests.get(
                f"{self.fulfillment_url}/order",
                headers=headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()

            orders_response = response.json()
            orders = orders_response.get("orders", [])

            return {
                "status": "success",
                "order_count": len(orders),
                "orders": orders
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

    def get_active_listings(self) -> Dict:
        """Fetch all active listings for the authenticated user."""
        try:
            headers = self._get_headers()

            response = requests.get(
                f"{self.base_url}/listing",
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            listings = response.json().get("listings", [])

            return {
                "status": "success",
                "listing_count": len(listings),
                "listings": listings
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

def _map_to_ebay_condition(condition: str) -> str:
    """Map product condition to eBay condition codes."""
    condition_lower = condition.lower()

    mapping = {
        "new": "NEW",
        "mint": "LIKE_NEW",
        "excellent": "LIKE_NEW",
        "very_good": "VERY_GOOD",
        "good": "GOOD",
        "fair": "ACCEPTABLE",
        "poor": "FOR_PARTS_OR_NOT_WORKING"
    }

    # Try exact match first
    if condition_lower in mapping:
        return mapping[condition_lower]

    # Try partial match
    for key, value in mapping.items():
        if key in condition_lower:
            return value

    return "USED_GOOD"  # Default

if __name__ == "__main__":
    print("eBay Inventory Connector")
    print("Requires authenticated EbayOAuthHandler instance")
