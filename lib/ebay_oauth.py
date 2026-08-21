"""eBay OAuth token exchange — refresh_token -> access_token using Basic Auth."""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request


def exchange_refresh_token(refresh_token: str, client_id: str, client_secret: str) -> str:
    """Exchange eBay refresh token for access token using Basic Auth.

    Returns the access_token string to use as Bearer token in API calls.
    Raises on any error from eBay.

    Uses HTTP Basic Auth (Authorization header) not body params — eBay rejects
    client credentials in the body with "client authentication failed".
    """
    url = "https://api.ebay.com/identity/v1/oauth2/token"

    # eBay requires Basic Auth: base64(client_id:client_secret) in Authorization header
    auth_bytes = f"{client_id}:{client_secret}".encode()
    auth_header = "Basic " + base64.b64encode(auth_bytes).decode()

    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": auth_header,
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result["access_token"]

    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        raise ValueError(f"eBay returned HTTP {e.code}: {body_text}")
    except Exception as e:
        raise ValueError(f"Token exchange failed: {e}")


if __name__ == "__main__":
    import os

    refresh_token = os.environ.get("EBAY_REFRESH_TOKEN")
    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print("ERROR: Missing EBAY_REFRESH_TOKEN, EBAY_CLIENT_ID, or EBAY_CLIENT_SECRET")
        exit(1)

    try:
        access_token = exchange_refresh_token(refresh_token, client_id, client_secret)
        print(f"Success: {access_token[:50]}...")
    except Exception as e:
        print(f"Failed: {e}")
        exit(1)
