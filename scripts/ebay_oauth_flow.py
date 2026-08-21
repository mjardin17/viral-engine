#!/usr/bin/env python3
"""Complete eBay OAuth flow — generates fresh refresh_token."""

import os
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import sys

CLIENT_ID = os.environ.get("EBAY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.account"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urlparse(self.path).query
        params = parse_qs(query)
        auth_code = params.get("code", [None])[0]

        if auth_code:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Success!</h1><p>You can close this window.</p>")
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Error</h1><p>No authorization code received.</p>")

    def log_message(self, format, *args):
        pass  # Suppress logging


def get_refresh_token():
    """Run the OAuth flow and return refresh_token."""
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set")
        return None

    # Step 1: Open browser for user to authorize
    auth_url = (
        f"https://auth.ebay.com/oauth2/authorize?"
        f"client_id={urllib.parse.quote(CLIENT_ID)}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"response_type=code&"
        f"scope={urllib.parse.quote(SCOPES)}"
    )

    print("Opening eBay login page...")
    print(f"If browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)

    # Step 2: Wait for callback
    server = HTTPServer(("localhost", 8765), CallbackHandler)
    print("Waiting for authorization code...")
    server.handle_request()
    server.server_close()

    if not auth_code:
        print("ERROR: No authorization code received")
        return None

    print(f"Got authorization code: {auth_code[:20]}...")

    # Step 3: Exchange code for refresh_token
    print("Exchanging code for refresh_token...")
    try:
        token_url = "https://api.ebay.com/identity/v1/oauth2/token"
        body = (
            "grant_type=authorization_code"
            f"&code={auth_code}"
            f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
            f"&client_id={urllib.parse.quote(CLIENT_ID)}"
            f"&client_secret={urllib.parse.quote(CLIENT_SECRET)}"
        )

        req = urllib.request.Request(
            token_url,
            data=body.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            refresh_token = result["refresh_token"]
            print(f"\n✅ SUCCESS!\n")
            print(f"EBAY_REFRESH_TOKEN={refresh_token}\n")
            print("Copy this into your .env.local file")
            return refresh_token

    except Exception as e:
        print(f"ERROR: {e}")
        return None


if __name__ == "__main__":
    refresh_token = get_refresh_token()
    if refresh_token:
        exit(0)
    else:
        exit(1)
