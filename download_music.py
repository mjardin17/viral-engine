#!/usr/bin/env python3
"""
download_music.py — Downloads battle music for Viral Engine renders.
Double-click this file to run it.
"""
import urllib.request
from pathlib import Path

MUSIC_DIR = Path(__file__).parent / "music"
MUSIC_DIR.mkdir(exist_ok=True)
OUT = MUSIC_DIR / "battle_epic.mp3"

TRACKS = [
    # Kevin MacLeod - Crusade (perfect for battle documentaries)
    ("Crusade - Kevin MacLeod",
     "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Crusade.mp3"),
    # Backup: Hitman
    ("Hitman - Kevin MacLeod",
     "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Hitman.mp3"),
    # Backup 2: Clash Defiant
    ("Clash Defiant - Kevin MacLeod",
     "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clash%20Defiant.mp3"),
]

print("Downloading battle music for Viral Engine...\n")

for name, url in TRACKS:
    print(f"Trying: {name}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) > 50_000:
            OUT.write_bytes(data)
            print(f"✓ Saved {len(data)//1024} KB → music/battle_epic.mp3")
            print(f"\nReady! Now run fix_audio_rerender.bat")
            break
        else:
            print(f"  Too small ({len(data)} bytes), trying next...")
    except Exception as e:
        print(f"  Failed: {e}")
else:
    print("\nAll downloads failed.")
    print("Manual download: https://incompetech.com/music/royalty-free/mp3-royaltyfree/Crusade.mp3")
    print(f"Save to: {OUT}")

input("\nPress Enter to close...")
