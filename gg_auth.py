"""
gg_auth.py — Standalone GG YouTube re-auth.
Opens Edge InPrivate directly. Never touches Chrome.
"""
import os
import pickle
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR   = Path(__file__).resolve().parent
CREDS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token_gg.pickle"
SCOPES     = ["https://www.googleapis.com/auth/youtube.upload",
               "https://www.googleapis.com/auth/youtube"]
REDIRECT   = "http://localhost:8080/"

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Users\jjard\AppData\Local\Microsoft\Edge\Application\msedge.exe",
]

def open_edge(url):
    for path in EDGE_PATHS:
        if os.path.exists(path):
            subprocess.Popen([path, "--inprivate", url])
            return True
    print(f"\nEdge not found. Paste this URL into Edge manually:\n{url}\n")
    return False

# Delete old token
if TOKEN_PATH.exists():
    TOKEN_PATH.unlink()
    print("Old token deleted.")

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
flow.redirect_uri = REDIRECT

auth_url, _ = flow.authorization_url(
    access_type="offline",
    prompt="select_account",
    login_hint="godsandgloryai@gmail.com",
)

print("\n" + "="*60)
print("  Opening Edge InPrivate...")
print("  Sign in as: godsandgloryai@gmail.com")
print("="*60 + "\n")

open_edge(auth_url)

print("Waiting for sign-in to complete...\n")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        self.server.callback_url = "http://localhost:8080" + self.path
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Done! Go back to the terminal.</h2>")

server = HTTPServer(("localhost", 8080), Handler)
server.handle_request()

flow.fetch_token(authorization_response=server.callback_url)

with open(TOKEN_PATH, "wb") as f:
    pickle.dump(flow.credentials, f)

print("\n✅  Token saved! Run VERIFY_GG.bat to confirm.")
input("\nPress ENTER to close.")
