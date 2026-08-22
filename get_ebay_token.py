#!/usr/bin/env python3
"""Get eBay refresh token with sell.fulfillment scope."""

import webbrowser
import os
from urllib.parse import urlencode, parse_qs, urlparse
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
REDIRECT_URI = "Joshua_Jardin-JoshuaJa-Empire-dahro"
SCOPES = [
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
]

if not CLIENT_ID or not CLIENT_SECRET:
    print("[ERROR] EBAY_CLIENT_ID or EBAY_CLIENT_SECRET not in .env")
    exit(1)

def step1_get_auth_url():
    """Step 1: Get authorization URL."""
    # eBay requires scopes as URL-encoded space-separated string
    scope_str = "%20".join(SCOPES)
    auth_url = (
        f"https://auth.ebay.com/oauth2/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope_str}"
    )
    return auth_url

def step2_user_authorizes(auth_url):
    """Step 2: Open browser for user to authorize."""
    print("\n[1] Opening eBay login in browser...")
    print(f"URL: {auth_url}\n")
    webbrowser.open(auth_url)
    print("[*] A browser window should have opened.")
    print("[*] Sign in and click 'Agree'")
    print("[*] You'll be redirected to a page with 'code=' in the URL")

def step3_get_code():
    """Step 3: Get authorization code from user."""
    print("\n[2] Copy the authorization code from the redirect URL.")
    print("    It looks like: code=...&expires_in=...")
    code = input("\nPaste the CODE value (the part between code= and &): ").strip()

    if not code:
        print("[ERROR] No code provided")
        return None

    return code

def step4_exchange_code(code):
    """Step 4: Exchange code for refresh token."""
    print(f"\n[3] Exchanging code for token...")

    import base64
    # eBay requires Basic Auth, not body params
    auth_str = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    response = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_str}",
        },
    )

    if response.status_code != 200:
        print(f"[ERROR] eBay returned {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        print("[ERROR] No refresh_token in response")
        print(data)
        return None

    return refresh_token

def step5_save_token(refresh_token):
    """Step 5: Save token to .env."""
    env_path = ".env"

    # Read current .env
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    # Replace or add EBAY_REFRESH_TOKEN
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("EBAY_REFRESH_TOKEN="):
            new_lines.append(f"EBAY_REFRESH_TOKEN={refresh_token}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"EBAY_REFRESH_TOKEN={refresh_token}\n")

    # Write back
    with open(env_path, "w") as f:
        f.writelines(new_lines)

    print(f"[OK] Token saved to {env_path}")
    print(f"[OK] EBAY_REFRESH_TOKEN={refresh_token}")

def main():
    print("=" * 70)
    print("eBay OAuth Token Generator (with sell.fulfillment scope)")
    print("=" * 70)

    # Step 1: Get auth URL
    auth_url = step1_get_auth_url()

    # Step 2: User authorizes
    step2_user_authorizes(auth_url)
    input("\nPress Enter when you've completed eBay authorization...")

    # Step 3: Get code
    code = step3_get_code()
    if not code:
        return

    # Step 4: Exchange for token
    refresh_token = step4_exchange_code(code)
    if not refresh_token:
        return

    # Step 5: Save to .env
    step5_save_token(refresh_token)

    print("\n" + "=" * 70)
    print("[OK] Done! Token is ready for sales tracking.")
    print("=" * 70)

if __name__ == "__main__":
    main()
