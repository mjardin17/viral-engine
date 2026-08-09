#!/usr/bin/env python3
"""Browser automation connectors for platforms without public APIs."""

import os
import json
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

try:
    from playwright.sync_api import sync_playwright, Browser, Page
except ImportError:
    print("⚠️ Playwright not installed. Run: pip install playwright")
    print("   Then run: playwright install")

from lib.platform_connectors import Listing, Sale, PlatformConnector


class BrowserConnector(PlatformConnector):
    """Base class for browser automation connectors."""

    def __init__(self, platform_name: str):
        super().__init__(platform_name)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def _start_browser(self):
        """Start Playwright browser."""
        if not self.browser:
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()

    def _stop_browser(self):
        """Stop Playwright browser."""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None

    def _login(self, username: str, password: str, login_url: str, username_selector: str, password_selector: str, submit_selector: str) -> bool:
        """Generic login method."""
        try:
            self._start_browser()
            self.page.goto(login_url, wait_until="networkidle")
            self.page.fill(username_selector, username)
            self.page.fill(password_selector, password)
            self.page.click(submit_selector)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False


class PoshmarkConnector(BrowserConnector):
    """Poshmark browser automation connector."""

    def __init__(self):
        super().__init__("poshmark")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Poshmark: No credentials configured (POSHMARK_USERNAME, POSHMARK_PASSWORD)")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(
                username, password,
                "https://poshmark.com/login",
                "input[name='username']",
                "input[name='password']",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://poshmark.com/listing/new", wait_until="networkidle")

            # Fill form
            self.page.fill("input[name='title']", title[:200])
            self.page.fill("textarea[name='description']", description[:2000])
            self.page.fill("input[name='price']", str(price))

            # Submit
            self.page.click("button[type='submit']")
            self.page.wait_for_load_state("networkidle")

            listing_id = self.page.url.split("/")[-1]
            print(f"✓ Poshmark: Created {listing_id}")
            return Listing(listing_id, "poshmark", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Poshmark error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://poshmark.com/listing/{listing_id}/edit", wait_until="networkidle")

            if "price" in kwargs:
                self.page.fill("input[name='price']", str(kwargs["price"]))

            self.page.click("button[type='submit']")
            return True
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://poshmark.com/listing/{listing_id}", wait_until="networkidle")
            self.page.click("button:has-text('Delete Listing')")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        try:
            self._start_browser()
            self.page.goto("https://poshmark.com/account/sales", wait_until="networkidle")

            sales = []
            # Parse sales from page
            sale_items = self.page.query_selector_all(".sale-item")
            for item in sale_items:
                sales.append(Sale(
                    str(item.get_attribute("data-id")),
                    "poshmark",
                    str(item.get_attribute("data-listing-id")),
                    str(item.get_attribute("data-listing-id")),
                    float(item.text_content().split("$")[1]),
                    1,
                    "poshmark_buyer",
                    datetime.now()
                ))
            print(f"📊 Poshmark: Found {len(sales)} sales")
            return sales
        except:
            return []

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://poshmark.com/account/inventory", wait_until="networkidle")

            listings = []
            listing_items = self.page.query_selector_all(".listing-item")
            for item in listing_items:
                listings.append(Listing(
                    str(item.get_attribute("data-id")),
                    "poshmark",
                    item.query_selector(".title").text_content(),
                    "",
                    float(item.query_selector(".price").text_content().replace("$", "")),
                    1,
                    [],
                    "active",
                    f"https://poshmark.com/listing/{item.get_attribute('data-id')}",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 Poshmark: Found {len(listings)} listings")
            return listings
        except:
            return []


class MercariConnector(BrowserConnector):
    """Mercari browser automation connector."""

    def __init__(self):
        super().__init__("mercari")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Mercari: No credentials configured (MERCARI_USERNAME, MERCARI_PASSWORD)")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(
                username, password,
                "https://www.mercariapp.com/auth/login",
                "input[type='email']",
                "input[type='password']",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.mercariapp.com/sell", wait_until="networkidle")

            self.page.fill("input[name='title']", title[:200])
            self.page.fill("textarea[name='description']", description[:2000])
            self.page.fill("input[name='price']", str(int(price)))

            self.page.click("button[type='submit']")
            self.page.wait_for_load_state("networkidle")

            listing_id = self.page.url.split("/")[-1]
            print(f"✓ Mercari: Created {listing_id}")
            return Listing(listing_id, "mercari", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Mercari error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.mercariapp.com/item/{listing_id}/edit", wait_until="networkidle")

            if "price" in kwargs:
                self.page.fill("input[name='price']", str(int(kwargs["price"])))

            self.page.click("button[type='submit']")
            return True
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.mercariapp.com/item/{listing_id}", wait_until="networkidle")
            self.page.click("button:has-text('Remove Listing')")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        return []

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.mercariapp.com/account/listings", wait_until="networkidle")

            listings = []
            listing_items = self.page.query_selector_all(".listing-card")
            for item in listing_items:
                listings.append(Listing(
                    str(item.get_attribute("data-id")),
                    "mercari",
                    item.query_selector(".title").text_content(),
                    "",
                    float(item.query_selector(".price").text_content().replace("¥", "")),
                    1,
                    [],
                    "active",
                    f"https://www.mercariapp.com/item/{item.get_attribute('data-id')}",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 Mercari: Found {len(listings)} listings")
            return listings
        except:
            return []


class DepopConnector(BrowserConnector):
    """Depop browser automation connector."""

    def __init__(self):
        super().__init__("depop")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Depop: No credentials configured (DEPOP_USERNAME, DEPOP_PASSWORD)")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(
                username, password,
                "https://www.depop.com/auth/login",
                "input[name='username']",
                "input[name='password']",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.depop.com/sell", wait_until="networkidle")

            self.page.fill("input[placeholder='Title']", title[:200])
            self.page.fill("textarea[placeholder='Description']", description[:2000])
            self.page.fill("input[type='number']", str(price))

            self.page.click("button:has-text('Post')")
            self.page.wait_for_load_state("networkidle")

            listing_id = self.page.url.split("/")[-1]
            print(f"✓ Depop: Created {listing_id}")
            return Listing(listing_id, "depop", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Depop error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.depop.com/edit/{listing_id}", wait_until="networkidle")

            if "price" in kwargs:
                self.page.fill("input[type='number']", str(kwargs["price"]))

            self.page.click("button:has-text('Save')")
            return True
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.depop.com/item/{listing_id}", wait_until="networkidle")
            self.page.click("button:has-text('Delete')")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        return []

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.depop.com/account/inventory", wait_until="networkidle")

            listings = []
            listing_items = self.page.query_selector_all("[data-testid='listing-card']")
            for item in listing_items:
                listings.append(Listing(
                    str(item.get_attribute("data-listing-id")),
                    "depop",
                    item.query_selector(".title").text_content(),
                    "",
                    float(item.query_selector(".price").text_content().replace("£", "")),
                    1,
                    [],
                    "active",
                    f"https://www.depop.com/item/{item.get_attribute('data-listing-id')}",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 Depop: Found {len(listings)} listings")
            return listings
        except:
            return []


class FacebookMarketplaceBrowserConnector(BrowserConnector):
    """Facebook Marketplace browser automation connector."""

    def __init__(self):
        super().__init__("facebook_web")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Facebook Marketplace: No credentials configured (FACEBOOK_EMAIL, FACEBOOK_PASSWORD)")
            return False
        try:
            email, password = self.auth_token.split(":", 1)
            return self._login(
                email, password,
                "https://www.facebook.com/login",
                "input[name='email']",
                "input[name='pass']",
                "button[name='login']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.facebook.com/marketplace/create", wait_until="networkidle")

            # Click on "For Sale"
            self.page.click("button:has-text('For Sale')")
            self.page.fill("input[aria-label='Title']", title[:200])
            self.page.fill("textarea[aria-label='Description']", description[:5000])
            self.page.fill("input[inputmode='decimal']", str(price))

            self.page.click("button:has-text('Post')")
            self.page.wait_for_load_state("networkidle")

            listing_id = self.page.url.split("/")[-1]
            print(f"✓ Facebook Marketplace: Created {listing_id}")
            return Listing(listing_id, "facebook_web", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Facebook Marketplace error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.facebook.com/marketplace/item/{listing_id}/edit", wait_until="networkidle")

            if "price" in kwargs:
                self.page.fill("input[inputmode='decimal']", str(kwargs["price"]))

            self.page.click("button:has-text('Save')")
            return True
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.facebook.com/marketplace/item/{listing_id}", wait_until="networkidle")
            self.page.click("button[aria-label='Delete']")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        return []

    def get_inventory(self) -> List[Listing]:
        return []


# Browser connector registry
BROWSER_CONNECTORS = {
    "poshmark_web": PoshmarkConnector,
    "mercari_web": MercariConnector,
    "depop_web": DepopConnector,
    "facebook_web": FacebookMarketplaceBrowserConnector,
}
