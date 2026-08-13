#!/usr/bin/env python3
"""
Commercial Generator: Creates render missions for product commercials.
Takes product info from Boss Listers and generates video render scripts.
"""

import json
from pathlib import Path
from datetime import datetime

def create_commercial_mission(product_name, product_description, price, image_urls, mission_id):
    """
    Create a render mission for a 30-second product commercial.

    Args:
        product_name: Name of the product (e.g., "Vintage Leather Jacket")
        product_description: Product details
        price: Selling price
        image_urls: List of product image URLs
        mission_id: Unique mission ID (e.g., "commercial-jacket-001")

    Returns:
        dict: Mission ready for MISSION_BOARD.json
    """

    # Generate commercial render script
    commercial_script = {
        "title": f"Product Commercial: {product_name}",
        "type": "commercial",
        "duration_seconds": 30,
        "scenes": [
            {
                "scene": 1,
                "duration": 3,
                "type": "title",
                "text": product_name,
                "background": "gradient_dark_gold"
            },
            {
                "scene": 2,
                "duration": 8,
                "type": "product_showcase",
                "product_images": image_urls[:3],
                "audio": "upbeat_music",
                "caption": "Premium quality"
            },
            {
                "scene": 3,
                "duration": 6,
                "type": "description",
                "text": product_description,
                "text_color": "gold",
                "audio": f"tts:Exquisite {product_name}. {product_description}"
            },
            {
                "scene": 4,
                "duration": 5,
                "type": "price_and_cta",
                "price": f"${price}",
                "text": "Available now on Boss Listers",
                "cta_button": "Buy Now",
                "audio": f"tts:Only {price} dollars"
            },
            {
                "scene": 5,
                "duration": 8,
                "type": "product_loop",
                "product_images": image_urls,
                "music": "upbeat_fade_out",
                "text": "Boss Listers: Curated, Affordable, Authentic"
            }
        ],
        "audio": {
            "music": "upbeat_modern",
            "voice": "professional_female",
            "volume_levels": {
                "music": 0.6,
                "voice": 1.0
            }
        },
        "output_formats": [
            {"format": "mp4_1080p", "platform": "instagram_feed"},
            {"format": "mp4_9_16", "platform": "tiktok"},
            {"format": "mp4_1_1", "platform": "instagram_reels"}
        ]
    }

    # Create mission
    mission = {
        "id": mission_id,
        "title": f"Commercial: {product_name}",
        "type": "commercial",
        "status": "pending",
        "priority": 2,
        "created_at": datetime.now().isoformat(),
        "product": {
            "name": product_name,
            "description": product_description,
            "price": price,
            "images": image_urls
        },
        "render_script": commercial_script,
        "channel": "COMMERCIALS",
        "publish_to": ["instagram", "tiktok", "youtube_shorts", "facebook"]
    }

    return mission

def add_to_mission_board(mission, mission_board_path="MISSION_BOARD.json"):
    """Add mission to MISSION_BOARD.json."""
    mission_board_path = Path(mission_board_path)

    # Load existing missions
    if mission_board_path.exists():
        with open(mission_board_path) as f:
            board = json.load(f)
    else:
        board = {"missions": []}

    # Check for duplicates
    if any(m.get("id") == mission["id"] for m in board.get("missions", [])):
        return False  # Mission already exists

    # Add new mission
    board["missions"].append(mission)

    # Save
    with open(mission_board_path, 'w') as f:
        json.dump(board, f, indent=2)

    return True

if __name__ == "__main__":
    # Example: Create a commercial for a leather jacket
    mission = create_commercial_mission(
        product_name="Vintage Leather Jacket",
        product_description="Classic brown leather jacket, excellent condition, perfect for fall",
        price=89.99,
        image_urls=[
            "https://example.com/jacket1.jpg",
            "https://example.com/jacket2.jpg",
            "https://example.com/jacket3.jpg"
        ],
        mission_id="commercial-jacket-001"
    )

    print(json.dumps(mission, indent=2))
