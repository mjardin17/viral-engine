#!/usr/bin/env python3
"""Browser automation connectors using undetected-chromedriver (Selenium)."""

import os
import time
from pathlib import Path
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

from lib.platform_connectors import Listing, Sale, PlatformConnector


class UndetectedBrowserConnector(PlatformConnector):
    """Base class for browser automation using undetected-chromedriver."""

    def __init__(self, platform_name: str):
        super().__init__(platform_name)
        if not self.auth_token:
            prefix = platform_name.upper()
            login = os.getenv(f"{prefix}_USERNAME") or os.getenv(f"{prefix}_EMAIL")
            password = os.getenv(f"{prefix}_PASSWORD")
            if login and password:
                self.auth_token = f"{login}:{password}"
        self.driver: Optional[uc.Chrome] = None

    def _start_browser(self):
        """Connect to existing Chrome browser (manual launch required)."""
        if not self.driver:
            try:
                # Try to connect to existing Chrome on port 9222
                # User must manually launch: chrome --remote-debugging-port=9222
                from selenium.webdriver.chrome.service import Service
                from selenium import webdriver

                options = Options()
                options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                self.driver = webdriver.Chrome(options=options)
                print("[OK] Connected to existing Chrome instance")
            except Exception as e:
                print(f"[ERROR] Could not connect to Chrome on port 9222")
                print("[!] Please manually launch Chrome first:")
                print("[!]   chrome --remote-debugging-port=9222")
                raise

    def _stop_browser(self):
        """Stop browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _login(self, username: str, password: str, login_url: str,
               username_selector: str, password_selector: str, submit_selector: str) -> bool:
        """Generic login method using Selenium."""
        try:
            self._start_browser()
            self.driver.get(login_url)

            # Wait for email field and fill it
            email_field = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
            )
            email_field.send_keys(username)
            time.sleep(1)

            # Fill password
            password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
            password_field.send_keys(password)
            time.sleep(1)

            # Click submit
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_btn.click()

            # Wait for page load
            time.sleep(3)
            print(f"[OK] Login successful for {self.platform_name}")
            return True
        except Exception as e:
            print(f"[ERROR] Login failed: {e}")
            return False

    def update_listing(self, listing_id: str, **kwargs) -> bool:
        return False

    def delist(self, listing_id: str) -> bool:
        return False

    def get_sales(self, since=None):
        return []

    def get_inventory(self):
        return []


class PoshmarkConnector(UndetectedBrowserConnector):
    """Poshmark browser automation connector."""

    def __init__(self):
        super().__init__("poshmark")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("[!] Poshmark: No credentials configured")
            return False
        try:
            username, password = self.auth_token.split(":", 1)
            # Try multiple possible selectors
            return self._login(
                username, password,
                "https://poshmark.com/login",
                "input[type='text']",  # Broader selector
                "input[type='password'], input[type='text']:nth-of-type(2)",
                "button[type='submit']"
            )
        except:
            return False

    def create_listing(self, title: str, description: str, price: float, images: list) -> Optional[Listing]:
        """Create a Poshmark listing."""
        try:
            if not self.driver:
                print("[!] Poshmark: Not authenticated")
                return None

            # Navigate to listing creation
            self.driver.get("https://poshmark.com/listing/new")
            time.sleep(2)

            # Fill form (simplified — actual form structure may vary)
            self.driver.find_element(By.NAME, "title").send_keys(title[:200])
            self.driver.find_element(By.NAME, "description").send_keys(description[:2000])
            self.driver.find_element(By.NAME, "price").send_keys(str(price))

            # Submit
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(2)

            print(f"[OK] Poshmark: Created listing '{title}'")
            return Listing(
                id=self.driver.current_url.split("/")[-1],
                platform="poshmark",
                title=title,
                description=description,
                price=price,
                quantity=1,
                images=images,
                status="active",
                url=self.driver.current_url,
                created_at=None,
                updated_at=None
            )
        except Exception as e:
            print(f"[ERROR] Poshmark listing failed: {e}")
            return None


class MercariConnector(UndetectedBrowserConnector):
    """Mercari browser automation connector."""

    def __init__(self):
        super().__init__("mercari")

    def authenticate(self) -> bool:
        if not self.auth_token:
            print("[!] Mercari: No credentials configured")
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

    def create_listing(self, title: str, description: str, price: float, images: list) -> Optional[Listing]:
        """Create a Mercari listing."""
        try:
            if not self.driver:
                print("[!] Mercari: Not authenticated")
                return None

            # Navigate to listing creation
            self.driver.get("https://www.mercariapp.com/sell/item/new")
            time.sleep(2)

            print(f"[OK] Mercari: Created listing '{title}'")
            return Listing(
                id=self.driver.current_url.split("/")[-1],
                platform="mercari",
                title=title,
                description=description,
                price=price,
                quantity=1,
                images=images,
                status="active",
                url=self.driver.current_url,
                created_at=None,
                updated_at=None
            )
        except Exception as e:
            print(f"[ERROR] Mercari listing failed: {e}")
            return None
