#!/usr/bin/env python3
"""
Scanner → Boss Listers Bridge
Automatically converts Epson scans into multi-platform listings.
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime

BOSS_LISTERS_DB = Path(__file__).parent.parent / "boss-listers-ai" / "data.json"

def create_marketplace_listings_from_scan(product: Dict) -> Dict:
    """
    Generate platform-specific listings from a single scanned product.
    Each platform has different character limits, formats, etc.
    """

    name = product.get("name", "Scanned Item")
    description = product.get("description", "")
    images = product.get("images", [])
    price = product.get("price", 0)
    category = product.get("category", "general")

    listings = {}

    # ============ FACEBOOK MARKETPLACE ============
    listings["facebook"] = {
        "title": name[:100],  # FB limit: 100 chars
        "description": f"{description}\n\n✅ Authentic\n📸 {len(images)} photos\n🚚 Ships fast",
        "price": price,
        "category": "for_sale",
        "condition": product.get("condition", "unknown"),
        "photos": images[:10]  # FB: 10 max
    }

    # ============ MERCARI ============
    listings["mercari"] = {
        "title": name[:60],  # Mercari limit: 60 chars
        "description": f"{description}\n\nCondition: {product.get('condition', 'Unknown')}\n\nShips within 2 days",
        "price": price,
        "category": _map_to_mercari_category(category),
        "condition": _map_to_mercari_condition(product.get("condition")),
        "photos": images[:12]  # Mercari: 12 max
    }

    # ============ POSHMARK ============
    listings["poshmark"] = {
        "title": name[:40],  # Poshmark limit: 40 chars
        "description": f"{description}\n\nAuthenticity: Guaranteed\nCondition: {product.get('condition', 'Unknown')}\n\nBundle for discounts!",
        "price": price,
        "category": _map_to_poshmark_category(category),
        "photos": images[:26]  # Poshmark: 26 max
    }

    # ============ DEPOP ============
    listings["depop"] = {
        "title": name[:80],
        "description": f"{description}\n\n✨ {product.get('condition', 'Unknown')} condition\n🔍 Authentic\n📦 Fast shipping",
        "price": price,
        "category": _map_to_depop_category(category),
        "photos": images[:10]
    }

    # ============ WHATNOT (AUCTION FORMAT) ============
    listings["whatnot"] = {
        "title": f"AUCTION: {name}",
        "description": f"Beautiful scanned {category}!\n\n{description}\n\nCondition: {product.get('condition', 'Unknown')}\n\nBid now!",
        "reserve_price": price * 0.75,  # Start lower for auction
        "estimated_final": price * 1.8,  # Expected multiplier
        "photos": images[:20],
        "auction_category": category,
        "auction_strategy": "VOLUME"  # Default strategy
    }

    # ============ ETSY ============
    listings["etsy"] = {
        "title": name[:141],  # Etsy limit: 141 chars
        "description": f"{description}\n\nAuthentic scanned product.\nCondition: {product.get('condition', 'Unknown')}\nShips worldwide.",
        "price": price,
        "tags": [category, "authentic", "scanned"],
        "photos": images[:10],
        "category": _map_to_etsy_category(category)
    }

    # ============ EBAY ============
    listings["ebay"] = {
        "title": name[:80],
        "description": f"{description}\n\nCondition: {product.get('condition', 'Unknown')}\nAuthentic.\nShips fast!\n\nThank you for bidding!",
        "price": price,
        "category": _map_to_ebay_category(category),
        "photos": images[:12],
        "condition": _map_to_ebay_condition(product.get("condition"))
    }

    # ============ PINTEREST ============
    listings["pinterest"] = {
        "title": name[:100],
        "description": f"Beautiful {category}! {description}",
        "link": "https://jardins-outpost.pages.dev",  # Link to your store
        "photos": images[:5]
    }

    # ============ REDDIT (r/marketplace) ============
    listings["reddit"] = {
        "title": f"[H] {name} [W] ${price}",  # Reddit marketplace format
        "description": f"{description}\n\nCondition: {product.get('condition', 'Unknown')}\nPrice: ${price}\n\nLocal pickup or ships!\nDM for details.",
        "photos": images[:4]
    }

    return listings

def auto_generate_price_suggestions(product: Dict) -> Dict:
    """
    Auto-suggest prices based on category + condition.
    Can be overridden manually.
    """
    category = product.get("category", "").lower()
    condition = product.get("condition", "unknown").lower()

    # Base price categories (conservative estimates)
    base_prices = {
        "collectibles": 75,
        "vintage": 45,
        "electronics": 60,
        "sporting": 35,
        "general": 25
    }

    base = base_prices.get(category, 25)

    # Condition multipliers
    condition_multipliers = {
        "mint": 2.0,
        "new": 1.8,
        "excellent": 1.5,
        "good": 1.1,
        "fair": 0.7,
        "unknown": 1.0
    }

    multiplier = condition_multipliers.get(condition, 1.0)
    suggested_price = base * multiplier

    # Platform pricing strategies
    platform_prices = {
        "facebook": suggested_price,
        "mercari": suggested_price * 0.95,  # Slightly lower
        "poshmark": suggested_price * 1.1,  # Slightly higher (designer audience)
        "depop": suggested_price * 1.05,
        "whatnot": suggested_price * 0.85,  # Start low for auction
        "etsy": suggested_price * 1.15,  # Premium for handmade/vintage
        "ebay": suggested_price,
        "reddit": suggested_price
    }

    return {
        "base_suggested": round(suggested_price, 2),
        "platform_pricing": {k: round(v, 2) for k, v in platform_prices.items()},
        "reasoning": f"Base ${base} × {multiplier:.1f}x ({condition} condition)"
    }

def _map_to_mercari_category(cat: str) -> str:
    mapping = {
        "collectibles": "Entertainment", "vintage": "Other",
        "electronics": "Electronics", "sporting": "Sports",
        "general": "Other"
    }
    return mapping.get(cat.lower(), "Other")

def _map_to_mercari_condition(cond: str) -> str:
    if not cond:
        return "Like New"
    cond_lower = cond.lower()
    if "mint" in cond_lower or "new" in cond_lower:
        return "Like New"
    elif "excellent" in cond_lower:
        return "Good"
    elif "good" in cond_lower:
        return "Fair"
    return "Fair"

def _map_to_poshmark_category(cat: str) -> str:
    mapping = {
        "collectibles": "Accessories", "vintage": "Vintage & Collectibles",
        "electronics": "Electronics", "sporting": "Sports",
    }
    return mapping.get(cat.lower(), "Accessories")

def _map_to_depop_category(cat: str) -> str:
    return cat.title() if cat else "Other"

def _map_to_etsy_category(cat: str) -> str:
    mapping = {
        "collectibles": "Collectibles", "vintage": "Vintage",
        "electronics": "Electronics", "sporting": "Sports Collectibles"
    }
    return mapping.get(cat.lower(), "Collectibles")

def _map_to_ebay_category(cat: str) -> str:
    # eBay category IDs - would be mapped in real implementation
    mapping = {
        "collectibles": 15687, "vintage": 45100,
        "electronics": 293, "sporting": 888
    }
    return mapping.get(cat.lower(), 1)

def _map_to_ebay_condition(cond: str) -> str:
    if not cond:
        return "3000"  # Used - Like New
    cond_lower = cond.lower()
    if "new" in cond_lower:
        return "1000"  # New
    elif "excellent" in cond_lower or "mint" in cond_lower:
        return "3000"  # Used - Like New
    elif "good" in cond_lower:
        return "4000"  # Used - Good
    return "5000"  # Used - Fair

def validate_listings(listings: Dict) -> Dict:
    """Validate that listings meet platform requirements."""
    validation = {}

    for platform, listing in listings.items():
        errors = []

        # Check required fields
        required_fields = {"title": str, "description": str}
        for field, field_type in required_fields.items():
            if field not in listing:
                errors.append(f"Missing {field}")

        # Platform-specific validation
        if platform == "facebook":
            if len(listing.get("title", "")) > 100:
                errors.append("Facebook title > 100 chars")
        elif platform == "poshmark":
            if len(listing.get("title", "")) > 40:
                errors.append("Poshmark title > 40 chars")

        validation[platform] = {
            "valid": len(errors) == 0,
            "errors": errors
        }

    return validation

if __name__ == "__main__":
    # Test
    test_product = {
        "name": "Vintage Star Wars Figure",
        "category": "collectibles",
        "condition": "mint",
        "description": "1985 original condition, still in original packaging",
        "images": ["photo1.jpg", "photo2.jpg"],
        "price": 50
    }

    listings = create_marketplace_listings_from_scan(test_product)
    prices = auto_generate_price_suggestions(test_product)

    print("Generated Listings:")
    print(json.dumps(listings, indent=2))
    print("\nPrice Suggestions:")
    print(json.dumps(prices, indent=2))
