#!/usr/bin/env python3
"""Council Bot 15: Login Coordinator - handles all platform logins via browser automation."""

import json
import csv
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright not installed. Run: INSTALL_PLAYWRIGHT.bat")
    exit(1)


class LoginCoordinator:
    """Coordinates logins across all platforms."""

    LOGIN_CONFIGS = {
        "poshmark": {
            "url": "https://poshmark.com/login",
            "username_selector": "input[name='username']",
            "password_selector": "input[name='password']",
            "submit_selector": "button[type='submit']",
            "success_check": "https://poshmark.com/",
        },
        "mercari": {
            "url": "https://www.mercariapp.com/auth/login",
            "username_selector": "input[type='email']",
            "password_selector": "input[type='password']",
            "submit_selector": "button[type='submit']",
            "success_check": "https://www.mercariapp.com/",
        },
        "depop": {
            "url": "https://www.depop.com/auth/login",
            "username_selector": "input[name='username']",
            "password_selector": "input[name='password']",
            "submit_selector": "button[type='submit']",
            "success_check": "https://www.depop.com/",
        },
        "facebook": {
            "url": "https://www.facebook.com/login",
            "username_selector": "input[name='email']",
            "password_selector": "input[name='pass']",
            "submit_selector": "button[name='login']",
            "success_check": "https://www.facebook.com/",
        },
        "etsy": {
            "url": "https://www.etsy.com/signin",
            "username_selector": "input[type='email']",
            "password_selector": "input[type='password']",
            "submit_selector": "button[type='submit']",
            "success_check": "https://www.etsy.com/",
        },
    }

    def __init__(self):
        self.results = {"successful": [], "failed": [], "mfa_required": []}
        self.session_dir = Path("sessions")
        self.session_dir.mkdir(exist_ok=True)

    def _load_accounts(self) -> List[Dict]:
        """Load accounts from CSV or JSON."""
        accounts = []

        # Try CSV first
        csv_path = Path("accounts.csv")
        if csv_path.exists():
            print("📋 Loading accounts from accounts.csv...")
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                accounts = list(reader)
            print(f"✓ Loaded {len(accounts)} accounts from CSV")
            return accounts

        # Try JSON
        json_path = Path("accounts.json")
        if json_path.exists():
            print("📋 Loading accounts from accounts.json...")
            with open(json_path) as f:
                accounts = json.load(f)
            print(f"✓ Loaded {len(accounts)} accounts from JSON")
            return accounts

        print("❌ No accounts.csv or accounts.json found")
        return []

    async def login_async(self, platform: str, username: str, password: str) -> bool:
        """Log in to a platform and save session (async)."""
        print(f"\n{'─'*70}")
        print(f"🔐 Logging in to {platform.upper()}")
        print(f"{'─'*70}")

        config = self.LOGIN_CONFIGS.get(platform)
        if not config:
            print(f"❌ Unknown platform: {platform}")
            self.results["failed"].append((platform, username, "Unknown platform"))
            return False

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Go to login page
                print(f"  → Navigating to {config['url']}...")
                await page.goto(config["url"], wait_until="networkidle", timeout=30000)

                # Fill username
                print(f"  → Entering credentials for {username}...")
                await page.fill(config["username_selector"], username)
                await asyncio.sleep(0.3)

                # Fill password
                await page.fill(config["password_selector"], password)
                await asyncio.sleep(0.3)

                # Submit
                print(f"  → Submitting login...")
                await page.click(config["submit_selector"])

                # Wait for navigation
                print(f"  → Waiting for login to complete...")
                await asyncio.sleep(2)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass  # Not all sites trigger networkidle

                # Check for success
                current_url = page.url
                if config["success_check"] in current_url:
                    print(f"  ✓ Successfully logged in to {platform}")

                    # Save cookies/session
                    cookies = await page.context.cookies()
                    session_file = self.session_dir / f"{platform}_{username}.json"
                    with open(session_file, "w") as f:
                        json.dump(cookies, f)
                    print(f"  ✓ Session saved to {session_file}")

                    self.results["successful"].append((platform, username))
                    await browser.close()
                    return True
                else:
                    # Check for MFA
                    if "verify" in current_url or "2fa" in current_url or "mfa" in current_url:
                        print(f"  ⚠️ MFA required - check your {platform} account for verification")
                        self.results["mfa_required"].append((platform, username))
                    else:
                        print(f"  ❌ Login failed - check credentials")
                        self.results["failed"].append((platform, username, f"Login failed or invalid credentials"))

                    await browser.close()
                    return False

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results["failed"].append((platform, username, str(e)))
            return False

    def login(self, platform: str, username: str, password: str) -> bool:
        """Log in to a platform (sync wrapper)."""
        return asyncio.run(self.login_async(platform, username, password))

    def run_all(self):
        """Log in to all accounts."""
        accounts = self._load_accounts()
        if not accounts:
            print("❌ No accounts to log in to")
            return

        print("\n" + "="*70)
        print("🤖 COUNCIL BOT 15: LOGIN COORDINATOR")
        print("="*70)
        print(f"\nLogging in to {len(accounts)} accounts across all platforms...\n")

        for i, account in enumerate(accounts, 1):
            platform = account.get("platform", "").lower()
            username = account.get("username") or account.get("email")
            password = account.get("password")

            if not all([platform, username, password]):
                print(f"\n⚠️ Skipping incomplete account entry: {account}")
                continue

            print(f"\n[{i}/{len(accounts)}] Logging in to {platform}...")
            self.login(platform, username, password)
            time.sleep(1)  # Rate limiting

        # Summary
        print("\n" + "="*70)
        print("📊 LOGIN SUMMARY")
        print("="*70)
        print(f"\n✓ Successful:    {len(self.results['successful'])} accounts")
        for platform, username in self.results["successful"]:
            print(f"    {platform:15s} → {username}")

        if self.results["mfa_required"]:
            print(f"\n⚠️ MFA Required:   {len(self.results['mfa_required'])} accounts")
            for platform, username in self.results["mfa_required"]:
                print(f"    {platform:15s} → {username} (manual approval needed)")

        if self.results["failed"]:
            print(f"\n❌ Failed:        {len(self.results['failed'])} accounts")
            for platform, username, reason in self.results["failed"]:
                print(f"    {platform:15s} → {username} ({reason})")

        print(f"\n{'='*70}")
        print(f"Council Bot 15 login coordinator completed")
        print(f"Sessions saved to: {self.session_dir}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    coordinator = LoginCoordinator()
    coordinator.run_all()
