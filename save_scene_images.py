#!/usr/bin/env python3
"""
save_scene_images.py — Drop images into a staging folder, run this, they get saved correctly.

Usage:
    1. Save your images to:  C:\Users\jjard\claude\video-bot-pipeline\stage\
       Name them ANYTHING — img001.jpg, screenshot.png, whatever.
    2. Run:  python save_scene_images.py
    3. Pick the episode and assign each image to a scene number.
    4. Done — images land in assets\{EPISODE}\ as scene_01.jpg etc.

The render pipeline checks assets\{EPISODE}\scene_XX.jpg before calling Pollinations,
so these images will be used automatically.
"""

import os
import shutil
from pathlib import Path

BASE   = Path(__file__).resolve().parent
STAGE  = BASE / "stage"
ASSETS = BASE / "assets"
CHARS  = BASE / "character_images"

# Scene titles per episode for easy reference
SCENE_TITLES = {
    "GG_EP001": {
         1: "The Pass — aerial opening",
         2: "The Persian Empire at Its Peak",
         3: "Who Were the Spartans",
         4: "Leonidas — King of Sparta",
         5: "Why Only 300 Spartans",
         6: "The Allied Greeks",
         7: "Day One — The Persians Arrive",
         8: "Day One — The Phalanx at Work",
         9: "Day One — The Immortals Fail",
        10: "Day Two — Same Result",
        11: "The Traitor — Ephialtes",
        12: "Why the Spartans Stayed",
        13: "Day Three — The Final Stand",
        14: "Xerxes's Revenge — Athens Burns",
        15: "Did Thermopylae Matter?",
        16: "The Monument",
        17: "Sparta's Aftermath",
        18: "What Happened to Ephialtes",
        19: "The Numbers",
        20: "Thermopylae in History",
        21: "What Thermopylae Actually Was",
        22: "Why This Still Matters",
        23: "Summary",
        24: "Next Episode — Salamis",
    },
    "GG_EP006": {
         1: "Opening Hook — Salamis Strait",
         2: "Recap — After Thermopylae",
         3: "Themistocles — Who Was He",
         4: "Evacuation of Athens",
         5: "The Persian Fleet Arrives",
         6: "The Lie to Xerxes",
         7: "The Strait — Why It Mattered",
         8: "Day of Battle — Greek Ships Move",
         9: "The Battle of Salamis",
        10: "Persian Fleet Destroyed",
        11: "Xerxes Watches His Fleet Burn",
        12: "Xerxes Retreats",
        13: "The Winter — Mardonius Stays",
        14: "The Battle of Plataea",
        15: "Mardonius Dies — Persians Routed",
        16: "Greece Is Free",
        17: "The Golden Age Begins",
        18: "Themistocles's Fate",
        19: "What Salamis Actually Was",
        20: "Modern Connection",
        21: "The Numbers",
        22: "Legacy",
        23: "Summary",
        24: "Next Episode — Gaugamela",
    },
}

def main():
    STAGE.mkdir(exist_ok=True)

    staged = sorted([
        f for f in STAGE.iterdir()
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    ])

    if not staged:
        print(f"\nNo images found in {STAGE}")
        print(f"Drop your images there (any filename) then run this script.\n")
        return

    print(f"\nFound {len(staged)} image(s) in stage/:")
    for i, f in enumerate(staged):
        print(f"  [{i+1}] {f.name}")

    print("\nEpisodes: GG_EP001, GG_EP006, ML_EP001, LO_EP001 (or type custom)")
    episode = input("Episode ID: ").strip().upper()
    if not episode:
        return

    out_dir = ASSETS / episode
    out_dir.mkdir(parents=True, exist_ok=True)

    titles = SCENE_TITLES.get(episode, {})

    print(f"\nAssign each image to a scene number (1-24). Press Enter to skip.\n")

    for img in staged:
        print(f"\n  Image: {img.name}")
        if titles:
            print("  Scene titles:")
            for num, title in titles.items():
                existing = out_dir / f"scene_{num:02d}.jpg"
                tag = " [HAS IMAGE]" if existing.exists() else ""
                print(f"    {num:2d}. {title}{tag}")

        raw = input("  → Scene number (or 'char NAME' to save to character_images): ").strip()

        if not raw:
            print("  Skipped.")
            continue

        if raw.lower().startswith("char "):
            name = raw[5:].strip()
            if not name.endswith((".jpg", ".png")):
                name += img.suffix
            dest = CHARS / name
            shutil.copy2(str(img), str(dest))
            print(f"  Saved to character_images/{name}")
        else:
            try:
                scene_num = int(raw)
            except ValueError:
                print("  Invalid. Skipped.")
                continue
            dest = out_dir / f"scene_{scene_num:02d}.jpg"
            shutil.copy2(str(img), str(dest))
            title = titles.get(scene_num, "")
            print(f"  ✓ Saved as assets/{episode}/scene_{scene_num:02d}.jpg  [{title}]")

    print(f"\nDone! Run:  python auto_render.py --episode {episode} --skip-images\n")


if __name__ == "__main__":
    main()
