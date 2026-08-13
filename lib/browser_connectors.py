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

from lib.platform_connectors import (
    Listing, Sale, PlatformConnector,
    GrailedConnector, VintedConnector, VestiaireConnector,
    EbayConnector, ReverbConnector, RealRealConnector, MercadoLibreConnector
)


class BrowserConnector(PlatformConnector):
    """Base class for browser automation connectors.

    Every subclass authenticates by splitting self.auth_token on ":" into
    username/password for Playwright form-filling. PlatformConnector.__init__
    only ever populates self.auth_token from {PLATFORM}_TOKEN, but every
    credential-setup script in agents/ writes {PLATFORM}_USERNAME and
    {PLATFORM}_PASSWORD as two separate variables instead — so auth_token was
    always None here and every browser connector failed regardless of what
    credentials existed. Fixed by constructing auth_token from the pair the
    tooling actually writes, so the unchanged split(":", 1) calls downstream
    now work.
    """

    def __init__(self, platform_name: str):
        super().__init__(platform_name)
        if not self.auth_token:
            prefix = platform_name.upper()
            # The setup scripts are inconsistent about which they write per
            # platform (MERCARI_EMAIL / FACEBOOK_EMAIL vs WHATNOT_USERNAME) —
            # accept either rather than guessing wrong per platform.
            login = os.getenv(f"{prefix}_USERNAME") or os.getenv(f"{prefix}_EMAIL")
            password = os.getenv(f"{prefix}_PASSWORD")
            if login and password:
                self.auth_token = f"{login}:{password}"
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
        # Was "facebook_web" — every other platform here matches its plain
        # lowercase name (poshmark, mercari, etsy...), and .env has plain
        # FACEBOOK_EMAIL/FACEBOOK_PASSWORD, not FACEBOOK_WEB_*. The suffix
        # meant this connector could never find its own credentials.
        super().__init__("facebook")

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


class WhatnotConnector(BrowserConnector):
    """Whatnot browser automation connector."""

    def __init__(self):
        super().__init__("whatnot")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Whatnot: No credentials configured (WHATNOT_USERNAME, WHATNOT_PASSWORD)")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(
                username, password,
                "https://www.whatnot.com/login",
                "input[name='username']",
                "input[name='password']",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.whatnot.com/selling/create-listing", wait_until="networkidle")

            # Fill form
            self.page.fill("input[name='title']", title[:200])
            self.page.fill("textarea[name='description']", description[:5000])
            self.page.fill("input[name='price']", str(price))

            # Submit
            self.page.click("button[type='submit']")
            self.page.wait_for_load_state("networkidle")

            listing_id = self.page.url.split("/")[-1]
            print(f"✓ Whatnot: Created {listing_id}")
            return Listing(listing_id, "whatnot", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Whatnot error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.whatnot.com/selling/edit/{listing_id}", wait_until="networkidle")

            if "price" in kwargs:
                self.page.fill("input[name='price']", str(kwargs["price"]))

            self.page.click("button[type='submit']")
            return True
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.whatnot.com/item/{listing_id}", wait_until="networkidle")
            self.page.click("button:has-text('Delete Listing')")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        try:
            self._start_browser()
            self.page.goto("https://www.whatnot.com/selling/sales", wait_until="networkidle")

            sales = []
            sale_items = self.page.query_selector_all(".sale-item")
            for item in sale_items:
                sales.append(Sale(
                    str(item.get_attribute("data-id")),
                    "whatnot",
                    str(item.get_attribute("data-listing-id")),
                    str(item.get_attribute("data-listing-id")),
                    float(item.text_content().split("$")[1]),
                    1,
                    "whatnot_buyer",
                    datetime.now()
                ))
            print(f"📊 Whatnot: Found {len(sales)} sales")
            return sales
        except:
            return []

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.whatnot.com/selling/inventory", wait_until="networkidle")

            listings = []
            listing_items = self.page.query_selector_all(".listing-item")
            for item in listing_items:
                listings.append(Listing(
                    str(item.get_attribute("data-id")),
                    "whatnot",
                    item.query_selector(".title").text_content(),
                    "",
                    float(item.query_selector(".price").text_content().replace("$", "")),
                    1,
                    [],
                    "active",
                    f"https://www.whatnot.com/item/{item.get_attribute('data-id')}",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 Whatnot: Found {len(listings)} listings")
            return listings
        except:
            return []


class EtsyBrowserConnector(BrowserConnector):
    """Etsy browser automation (no API key needed)."""
    def __init__(self):
        super().__init__("etsy")
    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Etsy: No credentials configured")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(username, password, "https://www.etsy.com/signin", "input[type='email']", "input[type='password']", "button[type='submit']")
        except: return False
    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.etsy.com/sell", wait_until="networkidle")
            self.page.fill("input[name='title']", title[:140])
            self.page.fill("textarea[name='description']", description[:2000])
            self.page.fill("input[name='price']", str(price))
            self.page.click("button[type='submit']")
            self.page.wait_for_load_state("networkidle")
            listing_id = self.page.url.split("/")[-1]
            print(f"✓ Etsy: Created {listing_id}")
            return Listing(listing_id, "etsy", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Etsy error: {e}")
            return None
    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.etsy.com/your/shops/0/listings/{listing_id}/edit", wait_until="networkidle")
            if "price" in kwargs:
                self.page.fill("input[name='price']", str(kwargs["price"]))
            self.page.click("button[type='submit']")
            return True
        except: return False
    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.etsy.com/your/shops/0/listings/{listing_id}", wait_until="networkidle")
            self.page.click("button:has-text('Deactivate')")
            return True
        except: return False
    def get_sales(self, since: datetime) -> List[Sale]: return []
    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.etsy.com/your/shops/0/listings/active", wait_until="networkidle")
            listings = []
            for item in self.page.query_selector_all(".listing-card"):
                listings.append(Listing(str(item.get_attribute("data-id")), "etsy", item.query_selector(".title").text_content(), "", 0.0, 1, [], "active", "", datetime.now(), datetime.now()))
            print(f"📋 Etsy: Found {len(listings)} listings")
            return listings
        except: return []


class PinterestBrowserConnector(BrowserConnector):
    """Pinterest browser automation (no API key needed)."""
    def __init__(self):
        super().__init__("pinterest")
    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Pinterest: No credentials configured")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(username, password, "https://www.pinterest.com/login/", "input[name='email']", "input[name='password']", "button[type='submit']")
        except: return False
    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.pinterest.com/pin/create/", wait_until="networkidle")
            self.page.fill("input[name='title']", title[:100])
            self.page.fill("textarea[name='description']", description[:500])
            self.page.click("button[type='submit']")
            self.page.wait_for_load_state("networkidle")
            pin_id = self.page.url.split("/")[-1]
            print(f"✓ Pinterest: Created {pin_id}")
            return Listing(pin_id, "pinterest", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Pinterest error: {e}")
            return None
    def update_listing(self, listing_id: str, **kwargs) -> bool: return True
    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.pinterest.com/pin/{listing_id}/", wait_until="networkidle")
            self.page.click("button:has-text('Delete')")
            return True
        except: return False
    def get_sales(self, since: datetime) -> List[Sale]: return []
    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.pinterest.com/me/pins/", wait_until="networkidle")
            listings = [Listing(str(item.get_attribute("data-id")), "pinterest", item.query_selector(".title").text_content(), "", 0.0, 1, [], "active", "", datetime.now(), datetime.now()) for item in self.page.query_selector_all(".pin")]
            print(f"📋 Pinterest: Found {len(listings)} pins")
            return listings
        except: return []


class RedditConnector(BrowserConnector):
    """Reddit r/marketplace and r/flipping browser connector."""

    def __init__(self):
        super().__init__("reddit")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Reddit: No credentials (REDDIT_USERNAME, REDDIT_PASSWORD)")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(
                username, password,
                "https://www.reddit.com/login",
                "input[name='username']",
                "input[name='password']",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.reddit.com/r/marketplace/submit", wait_until="networkidle")
            self.page.fill("input[placeholder='Post title']", f"[H] {title} [W] ${price}")
            self.page.fill("textarea", description)
            self.page.click("button:has-text('Post')")
            print(f"✓ Reddit: Posted {title}")
            return Listing("reddit_post", "reddit", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Reddit error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.reddit.com/r/marketplace/comments/{listing_id}", wait_until="networkidle")
            if "price" in kwargs:
                self.page.click("button:has-text('Edit')")
                self.page.wait_for_selector("textarea")
                self.page.fill("textarea", f"Updated price: ${kwargs['price']}")
                self.page.click("button:has-text('Save')")
            return True
        except:
            return False

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.reddit.com/r/marketplace/comments/{listing_id}", wait_until="networkidle")
            self.page.click("button:has-text('Delete')")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        return []  # Reddit doesn't track sales directly

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.reddit.com/user/me/submitted", wait_until="networkidle")
            listings = []
            posts = self.page.query_selector_all("[data-testid='post']")
            for post in posts[:20]:
                listings.append(Listing(
                    str(post.get_attribute("data-id")),
                    "reddit",
                    post.query_selector(".title").text_content() if post.query_selector(".title") else "",
                    "",
                    0.0,
                    1,
                    [],
                    "active",
                    "",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 Reddit: Found {len(listings)} posts")
            return listings
        except:
            return []


class LinkedInConnector(BrowserConnector):
    """LinkedIn marketplace connector for B2B reselling."""

    def __init__(self):
        super().__init__("linkedin")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ LinkedIn: No credentials (LINKEDIN_EMAIL, LINKEDIN_PASSWORD)")
            return False
        try:
            email, password = self.auth_token.split(":", 1)
            return self._login(
                email, password,
                "https://www.linkedin.com/login",
                "input[name='session_key']",
                "input[name='session_password']",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.linkedin.com/business/marketplace", wait_until="networkidle")
            self.page.click("button:has-text('Post')")
            self.page.fill("input[placeholder='Item title']", title[:100])
            self.page.fill("textarea", f"{description}\n\nPrice: ${price}")
            self.page.click("button:has-text('Publish')")
            print(f"✓ LinkedIn: Posted {title}")
            return Listing("linkedin_post", "linkedin", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ LinkedIn error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        return True  # LinkedIn updates through comments

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.linkedin.com/feed/update/{listing_id}", wait_until="networkidle")
            self.page.click("button[aria-label='Delete']")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        return []

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.linkedin.com/business/marketplace/my-listings", wait_until="networkidle")
            listings = []
            items = self.page.query_selector_all("[data-item]")
            for item in items[:50]:
                listings.append(Listing(
                    str(item.get_attribute("data-id")),
                    "linkedin",
                    item.query_selector(".title").text_content() if item.query_selector(".title") else "",
                    "",
                    0.0,
                    1,
                    [],
                    "active",
                    "",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 LinkedIn: Found {len(listings)} listings")
            return listings
        except:
            return []


class TwitchConnector(BrowserConnector):
    """Twitch clips and community posts connector."""

    def __init__(self):
        super().__init__("twitch")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Twitch: No credentials (TWITCH_USERNAME, TWITCH_PASSWORD)")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            return self._login(
                username, password,
                "https://www.twitch.tv/login",
                "input[name='login']",
                "input[name='password']",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.twitch.tv/creatorcamp/community/posts", wait_until="networkidle")
            self.page.click("button:has-text('Create Post')")
            self.page.fill("input[placeholder='Post title']", title)
            self.page.fill("textarea", f"{description}\n💰 Price: ${price}\n✨ DM for details!")
            self.page.click("button:has-text('Publish')")
            print(f"✓ Twitch: Posted {title}")
            return Listing("twitch_post", "twitch", title, description, price, 1, images, "active", self.page.url, datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Twitch error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        return True  # Twitch posts updated via edits

    def delist(self, listing_id: str) -> bool:
        try:
            self._start_browser()
            self.page.goto(f"https://www.twitch.tv/creatorcamp/community/posts/{listing_id}", wait_until="networkidle")
            self.page.click("button[aria-label='Delete']")
            return True
        except:
            return False

    def get_sales(self, since: datetime) -> List[Sale]:
        return []

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://www.twitch.tv/creatorcamp/community/posts", wait_until="networkidle")
            listings = []
            posts = self.page.query_selector_all("[data-post-id]")
            for post in posts[:50]:
                listings.append(Listing(
                    str(post.get_attribute("data-post-id")),
                    "twitch",
                    post.query_selector(".title").text_content() if post.query_selector(".title") else "",
                    "",
                    0.0,
                    1,
                    [],
                    "active",
                    "",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 Twitch: Found {len(listings)} posts")
            return listings
        except:
            return []


class DiscordConnector(BrowserConnector):
    """Discord community bot for marketplace listings."""

    def __init__(self):
        super().__init__("discord")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("⚠️ Discord: No bot token (DISCORD_BOT_TOKEN)")
            return False
        # Discord uses bot token auth, not browser login
        return True

    def create_listing(self, title: str, description: str, price: float, images: List[str]) -> Optional[Listing]:
        # This would use Discord API, not browser automation
        try:
            self._start_browser()
            # Post to #marketplace channel
            self.page.goto("https://discord.com/app", wait_until="networkidle")
            self.page.click("text=#marketplace")
            self.page.click("input[placeholder='Say something...']")
            embed = f"```\n{title} - ${price}\n{description}\n```"
            self.page.fill("input[placeholder='Say something...']", embed)
            self.page.press("input[placeholder='Say something...']", "Enter")
            print(f"✓ Discord: Posted {title}")
            return Listing("discord_msg", "discord", title, description, price, 1, images, "active", "discord://marketplace", datetime.now(), datetime.now())
        except Exception as e:
            print(f"❌ Discord error: {e}")
            return None

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        return True

    def delist(self, listing_id: str) -> bool:
        return True

    def get_sales(self, since: datetime) -> List[Sale]:
        return []

    def get_inventory(self) -> List[Listing]:
        try:
            self._start_browser()
            self.page.goto("https://discord.com/app", wait_until="networkidle")
            self.page.click("text=#marketplace")
            listings = []
            # Parse Discord messages for listings (simplified)
            messages = self.page.query_selector_all("[data-message-id]")
            for msg in messages[:20]:
                listings.append(Listing(
                    str(msg.get_attribute("data-message-id")),
                    "discord",
                    msg.text_content()[:100],
                    "",
                    0.0,
                    1,
                    [],
                    "active",
                    "",
                    datetime.now(),
                    datetime.now()
                ))
            print(f"📋 Discord: Found {len(listings)} messages")
            return listings
        except:
            return []


# Browser connector registry - ALL PLATFORMS (10+ platforms)
BROWSER_CONNECTORS = {
    "poshmark_web": PoshmarkConnector,
    "mercari_web": MercariConnector,
    "depop_web": DepopConnector,
    "facebook_web": FacebookMarketplaceBrowserConnector,
    "whatnot_web": WhatnotConnector,
    "etsy_web": EtsyBrowserConnector,
    "pinterest_web": PinterestBrowserConnector,
    "reddit_web": RedditConnector,
    "linkedin_web": LinkedInConnector,
    "twitch_web": TwitchConnector,
    "discord_web": DiscordConnector,
    "grailed_web": GrailedConnector,
    "vinted_web": VintedConnector,
    "vestiaire_web": VestiaireConnector,
    "ebay_web": EbayConnector,
    "reverb_web": ReverbConnector,
    "realreal_web": RealRealConnector,
    "mercadolibre_web": MercadoLibreConnector,
}
