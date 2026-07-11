# easy_youtube_uploader.py
# Claude Plug & Play Version - Just run it
import os
import sys
import time
import pickle
import subprocess
import webbrowser

# Always work from the folder this script lives in
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========================= EASY CONFIG =========================
FOLDER = r"C:\Users\jjard\claude\video-bot-pipeline\renders"
VIDEOS = [
    {"file": "GG_EP001_final.mp4", "title": "The 300: Last Stand at Thermopylae | Full Documentary | Gods & Glory"},
    {"file": "GG_EP002_final.mp4", "title": "Gaugamela: The Battle That Ended an Empire | Full Documentary | Gods & Glory"},
    {"file": "GG_EP003_final.mp4", "title": "Cannae: The Perfect Battle | Full Documentary | Gods & Glory"},
    {"file": "GG_EP004_final.mp4", "title": "The Mongol War Machine: How 100,000 Men Conquered the World | Full Documentary | Gods & Glory"},
    {"file": "GG_EP005_final.mp4", "title": "Constantinople 1453: The End of an Age | Full Documentary | Gods & Glory"},
]
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
UPLOADED_FILE = r"C:\Users\jjard\claude\video-bot-pipeline\uploaded_videos.json"

# Map filename → episode key for uploaded_videos.json
EP_KEY_MAP = {
    "GG_EP001_final.mp4": "EP001",
    "GG_EP002_final.mp4": "EP002",
    "GG_EP003_final.mp4": "EP003",
    "GG_EP004_final.mp4": "EP004",
    "GG_EP005_final.mp4": "EP005",
}
TOKEN_PATH = r"C:\Users\jjard\claude\video-bot-pipeline\token.pickle"
CREDS_PATH = r"C:\Users\jjard\claude\video-bot-pipeline\credentials.json"
# ===========================================================

def open_chrome(url):
    """Try to open Chrome specifically. Print URL as fallback."""
    print("\nIf Chrome doesn't open automatically, paste this URL into Chrome:")
    print(url + "\n")
    for chrome in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]:
        if os.path.exists(chrome):
            subprocess.Popen([chrome, url])
            return

def get_service():
    creds = None

    # Load saved token if it exists
    if os.path.exists(TOKEN_PATH):
        print("Loading saved login...")
        with open(TOKEN_PATH, 'rb') as f:
            creds = pickle.load(f)

    # Refresh expired token, or do full OAuth if none exists
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing token...")
            creds.refresh(Request())
        else:
            print("\nSIGN IN AS: godsandgloryai@gmail.com (Gods & Glory channel)\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)

            # Patch webbrowser so run_local_server opens Chrome, not Wave Browser
            _orig = webbrowser.open
            def _chrome(url, new=0, autoraise=True):
                open_chrome(url)
                return True
            webbrowser.open = _chrome

            creds = flow.run_local_server(port=8080, open_browser=True)
            webbrowser.open = _orig  # restore

        with open(TOKEN_PATH, 'wb') as f:
            pickle.dump(creds, f)
        print("Login saved.\n")

    return build('youtube', 'v3', credentials=creds)


def upload(youtube, file_path, title):
    body = {
        'snippet': {
            'title': title,
            'description': 'Full historical documentary from the Gods & Glory series.\n\n#History #Documentary #GodsAndGlory',
            'tags': ['history', 'documentary', 'gods and glory'],
            'categoryId': '27'
        },
        'status': {
            'privacyStatus': 'public',
            'madeForKids': False
        }
    }
    media = MediaFileUpload(file_path, resumable=True, chunksize=5*1024*1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    print(f"Uploading: {title}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Progress: {int(status.progress()*100)}%")
    video_id = response['id']
    print(f"DONE -> https://youtu.be/{video_id}\n")

    # Save ID to uploaded_videos.json
    ep_key = EP_KEY_MAP.get(os.path.basename(file_path))
    if ep_key:
        data = {}
        if os.path.exists(UPLOADED_FILE):
            with open(UPLOADED_FILE, 'r') as f:
                data = json.load(f)
        data[ep_key] = video_id
        with open(UPLOADED_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  Saved ID to uploaded_videos.json")


def main():
    print("=" * 60)
    print("  Gods & Glory YouTube Uploader")
    print("=" * 60 + "\n")
    try:
        youtube = get_service()
        print(f"Uploading {len(VIDEOS)} videos...\n")
        for i, v in enumerate(VIDEOS):
            file_path = os.path.join(FOLDER, v["file"])
            if not os.path.exists(file_path):
                print(f"  MISSING FILE: {v['file']} - skipping")
                continue
            size_mb = os.path.getsize(file_path) / (1024*1024)
            print(f"[{i+1}/{len(VIDEOS)}] {v['file']} ({size_mb:.0f}MB)")
            upload(youtube, file_path, v["title"])
            if i < len(VIDEOS) - 1:
                time.sleep(5)
        print("ALL DONE! Check your YouTube Studio.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\nTip: If auth error, delete token.pickle and run again.")

    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
