# youtube_upload_bot.py
# Clean YouTube Auto-Uploader for Gods & Glory Series
import os
import time
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
# ========================= CONFIG =========================
RENDERS_FOLDER = r"C:\Users\jjard\claude\video-bot-pipeline\renders"
VIDEOS = [
    {"file": "GG_EP001_final.mp4", "title": "The 300: Last Stand at Thermopylae | Full Documentary | Gods & Glory"},
    {"file": "GG_EP002_final.mp4", "title": "Gaugamela: The Battle That Ended an Empire | Full Documentary | Gods & Glory"},
    {"file": "GG_EP003_final.mp4", "title": "Cannae: The Perfect Battle | Full Documentary | Gods & Glory"},
    {"file": "GG_EP004_final.mp4", "title": "The Mongol War Machine: How 100,000 Men Conquered the World | Full Documentary | Gods & Glory"},
    {"file": "GG_EP005_final.mp4", "title": "Constantinople 1453: The End of an Age | Full Documentary | Gods & Glory"},
]
CATEGORY_ID = "27"  # Education
PRIVACY_STATUS = "public"
MADE_FOR_KIDS = False
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
# =======================================================
def get_youtube_service():
    token_path = "token.pickle"
    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError("Missing credentials.json - download from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)
    return build('youtube', 'v3', credentials=creds)

def upload_video(youtube, file_path, title, publish_at=None):
    body = {
        'snippet': {
            'title': title,
            'description': 'Full historical documentary from the Gods & Glory series.\n\n#History #Documentary #GodsAndGlory',
            'tags': ['history', 'documentary', 'gods and glory', 'ancient battles'],
            'categoryId': CATEGORY_ID
        },
        'status': {
            'privacyStatus': PRIVACY_STATUS,
            'madeForKids': MADE_FOR_KIDS,
            'publishAt': publish_at.isoformat() if publish_at else None
        }
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    print(f"📤 Uploading: {title}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Progress: {int(status.progress() * 100)}%")
    video_id = response['id']
    print(f"✅ SUCCESS → https://youtu.be/{video_id}\n")
    return video_id

def main():
    try:
        youtube = get_youtube_service()
        print("✅ Authenticated successfully\n")
        start_time = datetime.utcnow() + timedelta(hours=2)
        for i, video in enumerate(VIDEOS):
            file_path = os.path.join(RENDERS_FOLDER, video["file"])

            if not os.path.exists(file_path):
                print(f"⚠️ File not found: {file_path}")
                continue
            publish_at = start_time + timedelta(hours=48 * i)
            print(f"📅 Scheduled for: {publish_at.strftime('%Y-%m-%d %H:%M UTC')}")

            upload_video(youtube, file_path, video["title"], publish_at)

            if i < len(VIDEOS) - 1:
                time.sleep(8)
        print("🎉 All videos scheduled successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Tip: Place credentials.json in this folder and run the script again.")

if __name__ == "__main__":
    main()
