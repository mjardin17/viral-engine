# youtube_polish.py
# Applies SEO descriptions, chapter timestamps, thumbnails, and playlist
# to Gods & Glory Season 1 EP001-EP005
# Run after uploading — reads video IDs from uploaded_videos.json

import os
import sys
import json
import pickle
import subprocess
import webbrowser
import requests
import time
from pathlib import Path
from urllib.parse import quote

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(r"C:\Users\jjard\claude\video-bot-pipeline")
TOKEN_PATH = BASE_DIR / "token_polish.pickle"
CREDS_PATH = BASE_DIR / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/youtube"]
RENDERS_DIR = BASE_DIR / "renders"
UPLOADED_FILE = BASE_DIR / "uploaded_videos.json"

PLAYLIST_NAME = "Gods & Glory — Season 1"

# ─────────────────────────────────────────────────────────────
# EPISODE METADATA  (all written here — no AI API needed)
# ─────────────────────────────────────────────────────────────
EPISODES = {
    "EP001": {
        "title": "The 300: Last Stand at Thermopylae | Full Documentary | Gods & Glory",
        "description": """In 480 BC, a force of 300 Spartan warriors and their Greek allies stood against the largest army the ancient world had ever seen. The Battle of Thermopylae was not just a military engagement — it was a statement of will, sacrifice, and the price of freedom.

King Leonidas of Sparta knew his men could not win. But holding the narrow pass at Thermopylae long enough for Greece to prepare its defense was a mission worth dying for. For three days, the Spartans held. The legend they created has endured for 2,500 years.

This documentary explores the full story: the Persian invasion under Xerxes, Spartan military training and culture, the tactical genius of the Thermopylae position, the three-day battle, the betrayal by Ephialtes, and the final last stand. We also cover what happened after — the naval battle of Salamis and the ultimate Greek victory.

The 300 didn't stop Persia that day. But they gave Greece the time — and the inspiration — to fight back.

#GodsAndGlory #Thermopylae #Sparta #AncientGreece #History #DocumentaryHistory #AncientBattles #Leonidas #Xerxes #PersianWars #Spartans #HistoryDocumentary #BattleOfThermopylae #300Spartans #AncientHistory""",
        "tags": ["Thermopylae", "Sparta", "300 Spartans", "Leonidas", "Xerxes", "Persian Wars", "ancient Greece", "ancient battles", "history documentary", "Gods and Glory", "Greek history", "Battle of Thermopylae", "ancient history", "military history", "Persian Empire"],
        "chapters": """0:00 Introduction — The World at War
2:30 The Persian Empire Under Xerxes
6:15 Sparta — Warriors of the Ancient World
11:00 The Strategic Importance of Thermopylae
15:30 Day One — The First Assault
21:00 Day Two — The Spartans Hold
26:30 The Betrayal of Ephialtes
31:00 Day Three — The Final Stand
36:30 The Battle of Salamis
41:00 The Legacy of the 300
44:30 Conclusion — Why Thermopylae Still Matters""",
        "thumbnail_prompt": "Epic cinematic painting of 300 Spartan warriors in bronze armor holding spears at the narrow mountain pass of Thermopylae, Persian army stretching to the horizon behind them, dramatic golden sunset sky, ancient Greek battle scene, ultra detailed oil painting style, 8k",
    },
    "EP002": {
        "title": "Gaugamela: The Battle That Ended an Empire | Full Documentary | Gods & Glory",
        "description": """In 331 BC, on the plains of Gaugamela in modern-day Iraq, Alexander the Great faced an enemy force that outnumbered his army by perhaps five to one. What followed was not just a battle — it was the most decisive military victory in the ancient world, and it ended the Persian Empire forever.

Darius III of Persia had spent months preparing the battlefield. He had war elephants, scythed chariots, and an army drawn from every corner of his vast empire. Alexander had 47,000 men, unbreakable discipline, and a plan no one could have predicted.

This documentary follows the full story of Gaugamela: the rise of Alexander and his Macedonian army, the tactics of the oblique advance that split the Persian line, the moment Alexander personally led his cavalry charge toward Darius, and the psychological collapse of the largest empire on earth.

After Gaugamela, Persia was finished. Alexander would go on to conquer the known world. This is where it was decided.

#GodsAndGlory #Gaugamela #AlexanderTheGreat #PersianEmpire #History #HistoryDocumentary #AncientBattles #AncientHistory #Macedonia #Darius #MilitaryHistory #BattleOfGaugamela #GreekHistory #AncientWarfare #Conquest""",
        "tags": ["Gaugamela", "Alexander the Great", "Persian Empire", "Darius III", "Macedonia", "ancient battles", "ancient history", "history documentary", "Gods and Glory", "military history", "Battle of Gaugamela", "ancient warfare", "Greek history", "conquest", "Macedonian army"],
        "chapters": """0:00 Introduction — The World Alexander Inherited
2:45 The Macedonian War Machine
7:00 Darius III and the Persian Response
12:00 The March to Gaugamela
16:30 The Persian Battle Plan
21:00 Alexander's Oblique Advance
26:30 The Charge That Changed History
32:00 Collapse of the Persian Empire
37:30 The Fall of Persepolis
41:30 Alexander's World
44:00 Conclusion — The Battle That Decided Everything""",
        "thumbnail_prompt": "Alexander the Great on horseback charging into battle at Gaugamela, Macedonian phalanx with sarissas behind him, Persian army in chaos, dramatic lightning storm sky, epic cinematic oil painting, ultra detailed ancient warfare, 8k resolution",
    },
    "EP003": {
        "title": "Cannae: The Perfect Battle | Full Documentary | Gods & Glory",
        "description": """216 BC. The Roman Republic fields its largest army ever — 86,000 soldiers — to destroy the Carthaginian general who has been ravaging Italy for two years. Instead, Hannibal Barca annihilates them. The Battle of Cannae remains the most studied military engagement in history, taught in war colleges to this day.

Hannibal's genius was not overwhelming force — he was outnumbered. It was geometry. By deliberately weakening his center and strengthening his flanks, he created a trap that the Romans marched straight into. By the end of the day, over 50,000 Romans lay dead in just a few hours. It is one of the highest casualty rates in a single day of battle in human history.

This documentary covers the full Cannae story: Hannibal's march over the Alps, the Roman defeats at Trebia and Lake Trasimene, the political crisis in Rome, the battle itself in forensic detail, and why Rome survived even this catastrophe.

The perfect battle. The imperfect victory.

#GodsAndGlory #Cannae #Hannibal #Rome #PunicWars #History #HistoryDocumentary #AncientBattles #AncientHistory #MilitaryHistory #RomanHistory #Carthage #BattleOfCannae #AncientWarfare #RomanRepublic""",
        "tags": ["Cannae", "Hannibal", "Rome", "Punic Wars", "Roman Republic", "Carthage", "ancient battles", "history documentary", "Gods and Glory", "military history", "Battle of Cannae", "ancient warfare", "Roman history", "ancient history", "double envelopment"],
        "chapters": """0:00 Introduction — The Perfect Trap
2:30 Hannibal — Carthage's Greatest General
7:00 Crossing the Alps
12:00 Rome's Disasters — Trebia and Trasimene
17:30 Rome's Response — The Largest Army Ever
22:00 The Field at Cannae
26:30 Hannibal's Genius Plan
31:00 The Battle — A Masterclass in Encirclement
37:00 The Aftermath — Rome in Crisis
41:00 Why Rome Survived
44:00 Conclusion — Why Cannae Is Still Taught Today""",
        "thumbnail_prompt": "Hannibal Barca commanding battle at Cannae, Roman legions surrounded and trapped in a perfect encirclement, Carthaginian and African soldiers closing in, aerial view of the pincer movement, dramatic dark stormy sky, epic cinematic historical painting, 8k",
    },
    "EP004": {
        "title": "The Mongol War Machine: How 100,000 Men Conquered the World | Full Documentary | Gods & Glory",
        "description": """In the span of a single lifetime, the Mongols built the largest contiguous land empire in human history. Under Genghis Khan and his successors, armies that had never seen a city systematically dismantled every military force on earth — from the Jin Dynasty of China to the Khwarazmian Empire of Central Asia to the kingdoms of Eastern Europe.

How? The Mongol war machine was the most advanced military system of its age. Superior cavalry tactics, devastating psychological warfare, an intelligence network that mapped enemy territories before the army arrived, and a command structure that could adapt in real time on the battlefield.

This documentary breaks down the full system: how Genghis Khan unified the Mongol tribes, the revolutionary tactics that made their cavalry unstoppable, the siege warfare that allowed them to crack fortified cities, and the specific campaigns that shocked the civilized world.

The Mongols didn't just win battles. They changed the world.

#GodsAndGlory #Mongols #GenghisKhan #MongolEmpire #History #HistoryDocumentary #AncientBattles #MilitaryHistory #MongolWarMachine #Conquest #MedievalHistory #BattleHistory #MongolTactics #WarHistory #WorldHistory""",
        "tags": ["Mongols", "Genghis Khan", "Mongol Empire", "Mongol war machine", "medieval history", "military history", "history documentary", "Gods and Glory", "conquest", "cavalry tactics", "medieval warfare", "world history", "ancient battles", "battle history", "Mongol tactics"],
        "chapters": """0:00 Introduction — The World Before the Mongols
2:30 The Steppes — Where Warriors Are Born
7:00 Genghis Khan — Unifying the Tribes
12:30 The Mongol Army — Structure and Tactics
18:00 The Art of Mongol Warfare
23:30 The Fall of the Khwarazmian Empire
29:00 The Invasion of China
34:00 Into Europe — The World Trembles
39:00 Why No One Could Stop Them
43:00 The Legacy of the Mongol Empire
45:30 Conclusion""",
        "thumbnail_prompt": "Mongol cavalry charge at full gallop across the steppe, Genghis Khan on horseback leading thousands of warriors, burning city in the background, dramatic red and orange sky, epic cinematic oil painting of medieval warfare, ultra detailed, 8k",
    },
    "EP005": {
        "title": "Constantinople 1453: The End of an Age | Full Documentary | Gods & Glory",
        "description": """On May 29, 1453, the Ottoman Sultan Mehmed II did what no conqueror had managed in over a thousand years: he breached the walls of Constantinople. The city that had stood as the capital of the Roman Empire — and then the Byzantine Empire — fell after 53 days of siege. An age ended. A new world began.

Constantinople was more than a city. It was the last living link to the Roman Empire, the center of Orthodox Christianity, and the most fortified city in the medieval world. Its walls had never been broken. Its location at the crossroads of Europe and Asia made it the prize above all prizes.

Mehmed was just 21 years old. He brought gunpowder cannon — the largest ever built at that time — and a fleet that he dragged overland to bypass the city's harbor chain. He was willing to do whatever it took.

This documentary tells the complete story: the siege, the desperate defense, the final assault, and what the fall of Constantinople meant for the world — the end of the Middle Ages, the flight of Greek scholars to Italy, and the beginning of the Age of Exploration.

#GodsAndGlory #Constantinople #Mehmed #OttomanEmpire #ByzantineEmpire #History #HistoryDocumentary #1453 #FallOfConstantinople #MedievalHistory #MilitaryHistory #CrusadeHistory #RomanEmpire #Ottoman #WorldHistory""",
        "tags": ["Constantinople", "Mehmed II", "Ottoman Empire", "Byzantine Empire", "Fall of Constantinople", "1453", "medieval history", "history documentary", "Gods and Glory", "military history", "siege warfare", "medieval warfare", "Roman Empire", "Ottoman history", "world history"],
        "chapters": """0:00 Introduction — The Last City of Rome
3:00 Constantinople — A City Built to Never Fall
7:30 The Byzantine Empire in Its Final Days
12:00 Mehmed II — The Young Sultan with a Dream
16:30 The Siege Begins
21:00 The Great Cannon — Weapon That Changed Everything
26:00 The Naval Battle for the Harbor
30:30 53 Days — The Defense Crumbles
35:00 The Final Assault — May 29, 1453
40:00 The Fall and What Followed
43:30 The End of the Middle Ages
45:30 Conclusion — Why 1453 Still Matters""",
        "thumbnail_prompt": "Ottoman army besieging Constantinople in 1453, massive cannon firing at ancient city walls, Byzantine defenders on the ramparts, Ottoman fleet in the Golden Horn, dramatic smoke and fire, epic cinematic historical oil painting, ultra detailed, 8k",
    },
}


# ─────────────────────────────────────────────────────────────
# YOUTUBE AUTH
# ─────────────────────────────────────────────────────────────
def _open_chrome(url):
    print("\nIf Chrome doesn't open, paste this URL into Chrome manually:")
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
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("\nSIGN IN AS: justifiedmagnificent@gmail.com\n")
            print("(This auth is separate from the uploader — needed for full management access)\n")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            _orig = webbrowser.open
            def _chrome(url, new=0, autoraise=True):
                _open_chrome(url)
                return True
            webbrowser.open = _chrome
            creds = flow.run_local_server(port=8081, open_browser=True)
            webbrowser.open = _orig
        with open(TOKEN_PATH, 'wb') as f:
            pickle.dump(creds, f)
        print("Auth saved.\n")
    return build('youtube', 'v3', credentials=creds)


# ─────────────────────────────────────────────────────────────
# THUMBNAIL
# ─────────────────────────────────────────────────────────────
def download_thumbnail(ep_key, prompt, out_path):
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1280&height=720&nologo=true"
    print(f"  Generating thumbnail for {ep_key}...")
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            f.write(r.content)
        print(f"  Thumbnail saved: {out_path.name}")
        return True
    except Exception as e:
        print(f"  Thumbnail download failed: {e}")
        return False


def upload_thumbnail(youtube, video_id, thumb_path):
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumb_path), mimetype='image/jpeg')
        ).execute()
        print(f"  Thumbnail uploaded.")
    except Exception as e:
        print(f"  Thumbnail upload failed: {e}")


# ─────────────────────────────────────────────────────────────
# METADATA UPDATE
# ─────────────────────────────────────────────────────────────
def update_video(youtube, video_id, ep_data):
    full_description = ep_data['description'] + "\n\n" + ep_data['chapters']
    body = {
        'id': video_id,
        'snippet': {
            'title': ep_data['title'],
            'description': full_description,
            'tags': ep_data['tags'],
            'categoryId': '27',
            'defaultLanguage': 'en',
        }
    }
    try:
        youtube.videos().update(part='snippet', body=body).execute()
        print(f"  Metadata updated.")
    except Exception as e:
        print(f"  Metadata update failed: {e}")


# ─────────────────────────────────────────────────────────────
# PLAYLIST
# ─────────────────────────────────────────────────────────────
def get_or_create_playlist(youtube):
    # Check if playlist exists
    response = youtube.playlists().list(part='snippet', mine=True, maxResults=50).execute()
    for item in response.get('items', []):
        if item['snippet']['title'] == PLAYLIST_NAME:
            print(f"  Playlist already exists: {item['id']}")
            return item['id']

    # Create it
    playlist = youtube.playlists().insert(
        part='snippet,status',
        body={
            'snippet': {
                'title': PLAYLIST_NAME,
                'description': 'Full Season 1 of Gods & Glory — epic historical battle documentaries.',
                'defaultLanguage': 'en',
            },
            'status': {'privacyStatus': 'public'}
        }
    ).execute()
    print(f"  Playlist created: {playlist['id']}")
    return playlist['id']


def add_to_playlist(youtube, playlist_id, video_id, position):
    try:
        youtube.playlistItems().insert(
            part='snippet',
            body={
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {'kind': 'youtube#video', 'videoId': video_id},
                    'position': position
                }
            }
        ).execute()
        print(f"  Added to playlist at position {position}.")
    except Exception as e:
        print(f"  Playlist add failed: {e}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Gods & Glory — YouTube Polish")
    print("=" * 60 + "\n")

    # Load video IDs
    if not UPLOADED_FILE.exists():
        print(f"ERROR: {UPLOADED_FILE} not found.")
        print('Create it with format: {"EP001": "youtubeVideoId", ...}')
        input("\nPress Enter to close...")
        return

    with open(UPLOADED_FILE, 'r') as f:
        video_ids = json.load(f)

    print(f"Loaded {len(video_ids)} video IDs.\n")

    youtube = get_service()
    print("Authenticated.\n")

    # Create/find playlist
    print("Setting up playlist...")
    playlist_id = get_or_create_playlist(youtube)
    print()

    # Process each episode
    for position, (ep_key, ep_data) in enumerate(EPISODES.items()):
        if ep_key not in video_ids:
            print(f"[{ep_key}] No video ID found — skipping.")
            continue

        video_id = video_ids[ep_key]
        print(f"[{ep_key}] Processing: {video_id}")

        # Thumbnail
        thumb_path = RENDERS_DIR / f"thumbnail_{ep_key}.jpg"
        if download_thumbnail(ep_key, ep_data['thumbnail_prompt'], thumb_path):
            upload_thumbnail(youtube, video_id, thumb_path)

        # Metadata
        update_video(youtube, video_id, ep_data)

        # Playlist
        add_to_playlist(youtube, playlist_id, video_id, position)

        print(f"  Done.\n")
        time.sleep(2)

    print("=" * 60)
    print("  All done! Check YouTube Studio.")
    print("=" * 60)
    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
