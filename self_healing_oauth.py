"""
self_healing_oauth.py — Empire OS YouTube OAuth (godsandgloryai@gmail.com)
Self-healing: fixes missing deps, bad tokens, and wrong-account logins automatically.
"""
import os
import sys
import json
import pickle
import subprocess

TARGET_EMAIL = "godsandgloryai@gmail.com"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token_gg.pickle"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]
MAX_AUTH_ATTEMPTS = 3


def log(msg):
    print(f"[EMPIRE-OS] {msg}", flush=True)


# ---------- SELF-HEAL: dependencies ----------
def ensure_dependencies():
    required = {
        "google_auth_oauthlib": "google-auth-oauthlib",
        "googleapiclient": "google-api-python-client",
        "google.auth": "google-auth",
    }
    missing_pkgs = []
    for module, pip_name in required.items():
        try:
            __import__(module.split(".")[0])
        except ImportError:
            missing_pkgs.append(pip_name)

    if missing_pkgs:
        log(f"Missing packages detected: {missing_pkgs}. Installing automatically...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade"] + missing_pkgs, check=True)
        log("Dependencies installed. Re-run this script now.")
        sys.exit(0)
    log("All dependencies present.")


ensure_dependencies()

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# ---------- SELF-HEAL: credentials.json ----------
def ensure_credentials_file():
    if not os.path.exists(CREDENTIALS_FILE):
        log(f"ERROR: {CREDENTIALS_FILE} not found in {os.getcwd()}")
        log("Fix: download the Desktop-app OAuth client for godsandgloryai@gmail.com")
        log("from Google Cloud Console > APIs & Services > Credentials, save it here.")
        sys.exit(1)
    try:
        with open(CREDENTIALS_FILE) as f:
            data = json.load(f)
        if "installed" not in data:
            log("ERROR: credentials.json is a 'Web application' client, not 'Desktop app'.")
            log("Fix: create a new OAuth client of type 'Desktop app' in Google Cloud Console.")
            sys.exit(1)
    except json.JSONDecodeError:
        log("ERROR: credentials.json is corrupted/not valid JSON. Re-download it.")
        sys.exit(1)
    log("credentials.json OK.")


# ---------- SELF-HEAL: token load/refresh, discard if broken ----------
def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
        return creds
    except Exception as e:
        log(f"Existing token file is corrupted ({e}). Deleting and regenerating.")
        os.remove(TOKEN_FILE)
        return None


def save_token(creds):
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)
    log(f"Token saved to {TOKEN_FILE}")


def discard_token():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        log("Discarded bad/wrong-account token.")


def run_console_auth():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(prompt="consent")
    log("Open this URL in a browser logged into godsandgloryai@gmail.com:")
    print("\n" + auth_url + "\n")
    code = input("Paste the authorization code here: ").strip()
    flow.fetch_token(code=code)
    return flow.credentials


def get_valid_credentials():
    creds = load_token()

    if creds and creds.valid:
        log("Existing token is valid.")
        return creds

    if creds and creds.expired and creds.refresh_token:
        log("Token expired, attempting silent refresh...")
        try:
            creds.refresh(Request())
            save_token(creds)
            log("Refresh succeeded.")
            return creds
        except Exception as e:
            log(f"Refresh failed ({e}). Discarding token, starting fresh login.")
            discard_token()
            creds = None

    log("Starting new OAuth login flow...")
    try:
        creds = run_console_auth()
        save_token(creds)
        return creds
    except Exception as e:
        log(f"ERROR: auth flow failed: {e}")
        sys.exit(1)


# ---------- SELF-HEAL: wrong account -> auto retry ----------
def verify_and_self_heal():
    for attempt in range(1, MAX_AUTH_ATTEMPTS + 1):
        log(f"Verification attempt {attempt}/{MAX_AUTH_ATTEMPTS}")
        creds = get_valid_credentials()

        try:
            oauth2 = build("oauth2", "v2", credentials=creds)
            email = oauth2.userinfo().get().execute().get("email", "")
        except Exception as e:
            log(f"Could not read account email: {e}")
            discard_token()
            continue

        if email.lower() != TARGET_EMAIL:
            log(f"WRONG ACCOUNT: signed in as {email}, expected {TARGET_EMAIL}")
            log("Self-healing: discarding this token and forcing a new login...")
            discard_token()
            continue

        try:
            yt = build("youtube", "v3", credentials=creds)
            items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
        except Exception as e:
            log(f"YouTube API call failed: {e}")
            log("Fix: enable 'YouTube Data API v3' in Google Cloud Console > Library.")
            sys.exit(1)

        if not items:
            log("ERROR: No YouTube channel exists on this account.")
            sys.exit(1)

        channel = items[0]
        log("=" * 60)
        log(f"CHANNEL VERIFIED: {channel['snippet']['title']} (id={channel['id']})")
        log(f"ACCOUNT CONFIRMED: {email}")
        log("=" * 60)
        return creds

    log(f"FAILED after {MAX_AUTH_ATTEMPTS} attempts. Manually check which Google account")
    log(f"you're logged into in your browser — it must be {TARGET_EMAIL}.")
    sys.exit(1)


if __name__ == "__main__":
    log("Empire OS Self-Healing YouTube OAuth starting...")
    ensure_credentials_file()
    verify_and_self_heal()
    log("DONE. Token is valid, account and channel confirmed.")