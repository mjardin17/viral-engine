#!/usr/bin/env python3
"""
Automated environment setup and validation.
Checks prerequisites, creates .env template, validates connectivity.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Tuple

PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"
BOSS_LISTERS_DIR = PROJECT_ROOT / "boss-listers-ai"
BOSS_LISTERS_DB = BOSS_LISTERS_DIR / "data.json"

def check_python() -> bool:
    """Verify Python 3.8+ is available."""
    print("Checking Python...", end=" ", flush=True)
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ ({version.major}.{version.minor})")
        return True
    else:
        print(f"❌ Need Python 3.8+ (have {version.major}.{version.minor})")
        return False

def check_required_files() -> bool:
    """Verify all required files exist."""
    print("Checking files...", end=" ", flush=True)
    required = [
        "agents/video_pipeline_agent.py",
        "agents/crosslister_agent.py",
        "agents/platform_sync_agent.py",
        "agents/sales_tracker_agent.py",
        "agents/price_sync_agent.py",
        "lib/platform_connectors.py",
        "lib/commercial_generator.py",
        "START_AGENTS.bat",
        "AGENT_ECOSYSTEM.md",
        "PLATFORM_SETUP.md",
    ]

    missing = [f for f in required if not (PROJECT_ROOT / f).exists()]

    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
        return False
    else:
        print("✓")
        return True

def check_boss_listers() -> bool:
    """Verify Boss Listers inventory structure exists."""
    print("Checking inventory structure...", end=" ", flush=True)

    if not BOSS_LISTERS_DIR.exists():
        BOSS_LISTERS_DIR.mkdir(parents=True, exist_ok=True)

    if not BOSS_LISTERS_DB.exists():
        # Create sample inventory
        sample = {
            "products": [
                {
                    "id": "sample-jacket-001",
                    "name": "Vintage Leather Jacket",
                    "description": "Classic brown leather jacket in excellent condition",
                    "price": 89.99,
                    "quantity": 2,
                    "images": [
                        "https://via.placeholder.com/400x300?text=Jacket+Front",
                        "https://via.placeholder.com/400x300?text=Jacket+Back"
                    ],
                    "status": "for_sale",
                    "create_commercial": False,  # Set to true to auto-generate commercials
                    "sync_to_platforms": False  # Set to true to sync to all platforms
                }
            ]
        }

        with open(BOSS_LISTERS_DB, "w") as f:
            json.dump(sample, f, indent=2)

        print("✓ (created sample inventory)")
        return True
    else:
        print("✓")
        return True

def check_env_template() -> bool:
    """Create .env template if it doesn't exist."""
    if ENV_FILE.exists():
        print("Checking .env...", end=" ", flush=True)
        print("✓ (exists)")
        return True

    print("Creating .env template...", end=" ", flush=True)

    template = """# Empire OS Environment Variables
# This file stores sensitive credentials and should NOT be committed to git
# It's already in .gitignore, but never manually commit it

# ============ BUZZ RELAY (Required) ============
BUZZ_RELAY_URL=ws://localhost:3000
BUZZ_PRIVATE_KEY=31a697cb1a00d32c0ef5ef7b03dee1567e24d7798cb225302864f886d2af0f04

# ============ ETSY (Optional - live API ready) ============
# Get credentials from https://www.etsy.com/developers/app
# ETSY_TOKEN=<your-oauth-token>
# ETSY_SHOP_ID=<your-numeric-shop-id>

# ============ DEPOP (Optional - live API ready) ============
# Get credentials from https://www.depop.com/developer
# DEPOP_TOKEN=<your-api-token>

# ============ SHOPIFY (Optional - live API ready) ============
# Get credentials from Shopify admin > Apps > App and sales channel settings
# SHOPIFY_TOKEN=<your-access-token>
# SHOPIFY_STORE_NAME=<your-store.myshopify.com>

# ============ WOOCOMMERCE (Optional - live API ready) ============
# Get credentials from WooCommerce > Settings > Advanced > REST API
# WOOCOMMERCE_URL=https://your-store.com
# WOOCOMMERCE_KEY=<consumer-key>
# WOOCOMMERCE_SECRET=<consumer-secret>

# ============ MERCARI (Waiting for API access) ============
# MERCARI_TOKEN=<api-key-when-available>

# ============ POSHMARK (Waiting for API access) ============
# POSHMARK_TOKEN=<api-key-when-available>
"""

    with open(ENV_FILE, "w") as f:
        f.write(template)

    print("✓")
    return True

def check_buzz_connectivity() -> Tuple[bool, str]:
    """Check if Buzz relay is running and accessible."""
    print("Checking Buzz relay...", end=" ", flush=True)

    try:
        # Try to import websocket and connect
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=buzz-prod-relay"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if "buzz-prod-relay" in result.stdout:
            print("✓ (running in Docker)")
            return True, "Docker"
        else:
            print("⚠️ (not detected in Docker)")
            print("\n  To start Buzz relay:")
            print("    docker compose -f deploy/compose/compose.yml up -d")
            print("\n  Or check if it's running elsewhere at ws://localhost:3000")
            return False, "not running"

    except Exception as e:
        print(f"⚠️ (could not verify: {str(e)[:30]})")
        return False, "unknown"

def check_directories() -> bool:
    """Verify all required directories exist."""
    print("Checking directories...", end=" ", flush=True)

    required_dirs = [
        "agents",
        "lib",
        "renders",
        "output",
        "social_clips",
        "boss-listers-ai",
    ]

    for dir_name in required_dirs:
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

    print("✓")
    return True

def check_gitignore() -> bool:
    """Verify .env is in .gitignore."""
    print("Checking .gitignore...", end=" ", flush=True)

    gitignore = PROJECT_ROOT / ".gitignore"
    if gitignore.exists():
        with open(gitignore) as f:
            content = f.read()
            if ".env" in content:
                print("✓")
                return True

    print("⚠️ (.env not in .gitignore)")
    return False

def print_summary(checks: Dict[str, bool]):
    """Print summary of checks."""
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    for check, result in checks.items():
        status = "✓" if result else "❌"
        print(f"{status} {check}")

    print(f"\n{passed}/{total} checks passed")

    if passed == total:
        print("\n✓ Environment ready!")
        print("\nNext steps:")
        print("  1. Run: python setup_credentials.py")
        print("  2. Enter credentials for platforms you want to sync")
        print("  3. Run: START_AGENTS.bat")
        print("  4. Add items to boss-listers-ai/data.json")
        print("  5. Watch Buzz at http://localhost:3000")
        return True
    else:
        print("\n❌ Some checks failed. Fix issues above and try again.")
        return False

def main():
    """Run all environment checks."""
    print("\n" + "=" * 60)
    print("Empire OS Environment Setup")
    print("=" * 60 + "\n")

    checks = {
        "Python 3.8+": check_python(),
        "Required files": check_required_files(),
        "Boss Listers inventory": check_boss_listers(),
        "Directories": check_directories(),
        ".env template": check_env_template(),
        ".gitignore protection": check_gitignore(),
    }

    buzz_ok, buzz_status = check_buzz_connectivity()
    checks["Buzz relay"] = buzz_ok

    success = print_summary(checks)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
