#!/usr/bin/env python3
"""
eBay OAuth 2.0 Handler
Manages authentication, token refresh, and secure credential storage.
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta
import base64

EBAY_SANDBOX_AUTH = "https://auth.sandbox.ebay.com/oauth2/authorize"
EBAY_PRODUCTION_AUTH = "https://auth.ebay.com/oauth2/authorize"

EBAY_SANDBOX_TOKEN = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
EBAY_PRODUCTION_TOKEN = "https://api.ebay.com/identity/v1/oauth2/token"

CREDENTIALS_FILE = Path.home() / ".ebay_credentials.json"

class EbayOAuthHandler:
    """Manages eBay OAuth 2.0 authentication and token lifecycle."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/ebay_oauth", use_sandbox: bool = False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.use_sandbox = use_sandbox

        # Endpoints
        if use_sandbox:
            self.auth_endpoint = EBAY_SANDBOX_AUTH
            self.token_endpoint = EBAY_SANDBOX_TOKEN
        else:
            self.auth_endpoint = EBAY_PRODUCTION_AUTH
            self.token_endpoint = EBAY_PRODUCTION_TOKEN

        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.credentials_file = CREDENTIALS_FILE

        self._load_stored_credentials()

    def get_auth_url(self, scopes: list = None) -> str:
        """
        Generate eBay OAuth authorization URL.

        Scopes:
        - https://api.ebay.com/oauth/api_scope (Read user data)
        - https://api.ebay.com/oauth/api_scope/sell.inventory (Manage inventory)
        - https://api.ebay.com/oauth/api_scope/sell.inventory.readonly (Read inventory)
        - https://api.ebay.com/oauth/api_scope/sell.account (Manage account)
        - https://api.ebay.com/oauth/api_scope/sell.fulfillment (Manage orders)
        """
        if not scopes:
            scopes = [
                "https://api.ebay.com/oauth/api_scope/sell.inventory",
                "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
                "https://api.ebay.com/oauth/api_scope/sell.account"
            ]

        scope_str = " ".join(scopes)

        auth_url = (
            f"{self.auth_endpoint}?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={scope_str}&"
            f"state=RANDOM_STATE"
        )

        return auth_url

    def get_access_token_with_auth_code(self, auth_code: str) -> Dict:
        """
        Exchange authorization code for access token and refresh token.
        This is called after user approves the OAuth consent.
        """
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri
        }

        try:
            response = requests.post(self.token_endpoint, headers=headers, data=data, timeout=10)
            response.raise_for_status()

            token_response = response.json()

            # Store tokens
            self.access_token = token_response.get("access_token")
            self.refresh_token = token_response.get("refresh_token")

            # Calculate expiry (usually 2 hours for eBay)
            expires_in = token_response.get("expires_in", 7200)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

            # Save credentials
            self._save_credentials()

            return {
                "status": "success",
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_in": expires_in,
                "token_expiry": self.token_expiry.isoformat()
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            print("❌ No refresh token available")
            return False

        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        try:
            response = requests.post(self.token_endpoint, headers=headers, data=data, timeout=10)
            response.raise_for_status()

            token_response = response.json()

            self.access_token = token_response.get("access_token")
            expires_in = token_response.get("expires_in", 7200)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

            self._save_credentials()

            print(f"✅ Token refreshed. Expires in {expires_in} seconds")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Token refresh failed: {e}")
            return False

    def is_token_valid(self) -> bool:
        """Check if current token is still valid."""
        if not self.access_token or not self.token_expiry:
            return False

        # Refresh if expiry is within 5 minutes
        time_until_expiry = (self.token_expiry - datetime.now()).total_seconds()

        if time_until_expiry < 300:  # Less than 5 minutes
            return self.refresh_access_token()

        return time_until_expiry > 0

    def get_valid_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        if self.is_token_valid():
            return self.access_token
        return None

    def _save_credentials(self):
        """Securely save tokens to disk."""
        creds = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry.isoformat() if self.token_expiry else None,
            "client_id": self.client_id,
            "use_sandbox": self.use_sandbox,
            "saved_at": datetime.now().isoformat()
        }

        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(creds, f, indent=2)
            # Restrict file permissions to owner only (0600)
            os.chmod(self.credentials_file, 0o600)
            print(f"✅ Credentials saved to {self.credentials_file}")
        except Exception as e:
            print(f"❌ Failed to save credentials: {e}")

    def _load_stored_credentials(self):
        """Load previously saved tokens from disk."""
        if not self.credentials_file.exists():
            return

        try:
            with open(self.credentials_file) as f:
                creds = json.load(f)

            self.access_token = creds.get("access_token")
            self.refresh_token = creds.get("refresh_token")

            if creds.get("token_expiry"):
                self.token_expiry = datetime.fromisoformat(creds["token_expiry"])

            print(f"✅ Loaded stored eBay credentials")
            print(f"   Sandbox mode: {self.use_sandbox}")
            print(f"   Token expires: {self.token_expiry}")

            # Validate and refresh if needed
            if not self.is_token_valid():
                print("⚠️ Token is invalid or expired. Refresh required.")

        except Exception as e:
            print(f"⚠️ Failed to load credentials: {e}")

    def get_user_info(self) -> Dict:
        """Verify credentials are valid by fetching user info."""
        token = self.get_valid_token()
        if not token:
            return {"status": "error", "reason": "No valid token"}

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(
                "https://api.ebay.com/identity/v1/user" if not self.use_sandbox
                else "https://api.sandbox.ebay.com/identity/v1/user",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            user_info = response.json()
            return {"status": "success", "user": user_info}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

    def __str__(self):
        return (
            f"eBayOAuth("
            f"sandbox={self.use_sandbox}, "
            f"token_valid={self.is_token_valid()}, "
            f"expires={self.token_expiry}"
            ")"
        )

if __name__ == "__main__":
    # Example usage (requires credentials)
    print("eBay OAuth Handler initialized")
    print("To use: pass client_id, client_secret, and redirect_uri")
