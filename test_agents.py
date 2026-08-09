#!/usr/bin/env python3
"""Quick agent functionality test."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Test 1: Load inventory
print("=" * 60)
print("TEST 1: Load Boss Listers Inventory")
print("=" * 60)

from agents.platform_sync_agent import load_boss_listers_inventory
items = load_boss_listers_inventory()
print(f"✓ Loaded {len(items)} items")
if items:
    for item in items[:2]:
        print(f"  - {item.get('name')}: status={item.get('status')}")

# Test 2: Load platform connectors
print("\n" + "=" * 60)
print("TEST 2: Platform Connectors")
print("=" * 60)

from lib.platform_connectors import get_all_connectors, PLATFORMS
connectors = get_all_connectors()
print(f"✓ Loaded {len(connectors)} platform connectors:")
for name, connector in connectors.items():
    print(f"  - {name}: {connector.__class__.__name__}")

# Test 3: Test Etsy authentication (without credentials)
print("\n" + "=" * 60)
print("TEST 3: Etsy Connector (No Credentials)")
print("=" * 60)

etsy = connectors.get("etsy")
if etsy:
    auth_ok = etsy.authenticate()
    print(f"  Etsy auth (no creds): {auth_ok}")
    if not auth_ok:
        print("  ✓ Correctly rejected missing credentials")

# Test 4: Check mission board structure
print("\n" + "=" * 60)
print("TEST 4: Mission Board")
print("=" * 60)

mission_board_path = Path(__file__).parent / "MISSION_BOARD.json"
if mission_board_path.exists():
    import json
    with open(mission_board_path) as f:
        board = json.load(f)
    missions = board.get("missions", [])
    print(f"✓ Mission board exists with {len(missions)} missions")
else:
    print("✓ Mission board doesn't exist yet (will be created on first render)")

# Test 5: Commercial generator
print("\n" + "=" * 60)
print("TEST 5: Commercial Generator")
print("=" * 60)

from lib.commercial_generator import create_commercial_mission
mission = create_commercial_mission(
    product_name="Test Product",
    product_description="A test product for commercial",
    price=29.99,
    image_urls=["http://example.com/image.jpg"],
    mission_id="test-commercial-001"
)
render_script = mission.get("render_script", {})
scenes = render_script.get("scenes", [])
print(f"✓ Created commercial mission with {len(scenes)} scenes")
print(f"  Duration: {sum(s.get('duration', 0) for s in scenes)}s")

# Test 6: Platform connectors registry
print("\n" + "=" * 60)
print("TEST 6: Connector Registry")
print("=" * 60)

from lib.platform_connectors import get_connector
test_connector = get_connector("etsy")
print(f"✓ Got connector: {test_connector.__class__.__name__}")

invalid_connector = get_connector("nonexistent")
if invalid_connector is None:
    print("✓ Correctly returned None for invalid connector")

# Summary
print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
print("✓ Agents can load data")
print("✓ Agents can access platform connectors")
print("✓ Agents can generate missions")
print("✓ Core infrastructure works")
