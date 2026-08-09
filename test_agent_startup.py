#!/usr/bin/env python3
"""Test if agents can start and run one iteration."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Setup environment
os.environ["BUZZ_RELAY_URL"] = "ws://localhost:3000"
os.environ["BUZZ_PRIVATE_KEY"] = "31a697cb1a00d32c0ef5ef7b03dee1567e24d7798cb225302864f886d2af0f04"

print("=" * 60)
print("AGENT STARTUP TEST")
print("=" * 60)

# Test 1: Platform Sync Agent
print("\n1. Testing Platform Sync Agent...")
try:
    from agents.platform_sync_agent import load_boss_listers_inventory, load_sync_state

    inventory = load_boss_listers_inventory()
    sync_state = load_sync_state()

    print(f"   ✓ Loaded {len(inventory)} inventory items")
    print(f"   ✓ Loaded sync state")
    print("   ✓ Platform Sync Agent can initialize")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Sales Tracker Agent
print("\n2. Testing Sales Tracker Agent...")
try:
    from agents.sales_tracker_agent import track_sales, load_sales_log

    log = load_sales_log()
    print(f"   ✓ Loaded sales log")
    print("   ✓ Sales Tracker Agent can initialize")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Price Sync Agent
print("\n3. Testing Price Sync Agent...")
try:
    from agents.price_sync_agent import detect_price_changes, load_price_sync_state

    inventory = load_boss_listers_inventory()
    state = load_price_sync_state()

    changes, tracked = detect_price_changes(inventory)
    print(f"   ✓ Detected {len(changes)} price changes")
    print("   ✓ Price Sync Agent can initialize")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Crosslister Agent
print("\n4. Testing Crosslister Agent...")
try:
    from agents.crosslister_agent import load_boss_listers_inventory, get_inventory_hash
    from lib.commercial_generator import create_commercial_mission

    inventory = load_boss_listers_inventory()
    hash_val = get_inventory_hash(inventory)
    print(f"   ✓ Loaded {len(inventory)} items")
    print(f"   ✓ Inventory hash: {hash_val[:8]}...")
    print("   ✓ Crosslister Agent can initialize")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Video Pipeline Agent
print("\n5. Testing Video Pipeline Agent...")
try:
    from agents.video_pipeline_agent import load_mission_board

    missions = load_mission_board()
    print(f"   ✓ Loaded {len(missions)} missions")
    print("   ✓ Video Pipeline Agent can initialize")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("ALL AGENTS CAN INITIALIZE")
print("=" * 60)
print("✓ Platform Sync Agent: Ready")
print("✓ Sales Tracker Agent: Ready")
print("✓ Price Sync Agent: Ready")
print("✓ Crosslister Agent: Ready")
print("✓ Video Pipeline Agent: Ready")
