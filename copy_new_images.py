#!/usr/bin/env python3
"""
copy_new_images.py — Copies today's generated PNG files from Downloads
to character_images with proper scene names.

Double-click this file in File Explorer to run it.
"""
import shutil
from pathlib import Path
from datetime import datetime, date

DOWNLOADS = Path.home() / "Downloads"
CHARS_DIR = Path(__file__).parent / "character_images"

# Order: most recent first (script sorts by mtime descending).
# Generated in this order: EP002 sc14-24, EP003 sc16-24, EP004 sc16-24, EP005 sc18-24
# So EP005 scene 24 is the NEWEST → index 0 here.

BATCH_NAMES = [
    # ── EP005 Constantinople sc18-24 (most recent, generated last) ───────
    "constantinople_next_episode.png",            # 524
    "constantinople_legacy_summary.png",          # 523
    "constantinople_hinge_of_history.png",        # 522
    "constantinople_renaissance_connection.png",  # 521
    "constantinople_ottoman_rise.png",            # 520
    "constantinople_scholars_flee_west.png",      # 519
    "constantinople_mehmed_enters.png",           # 518
    # ── EP004 Mongols sc16-24 ────────────────────────────────────────────
    "mongols_modern_legacy_genetics.png",         # 424
    "mongols_death_toll_reckoning.png",           # 423
    "mongols_khanates_collapse.png",              # 422
    "mongols_black_death_connection.png",         # 421
    "mongols_pax_mongolica_silk_road.png",        # 420
    "mongols_kublai_yuan_dynasty.png",            # 419
    "mongols_empire_fractures.png",               # 418
    "mongols_ain_jalut_defeat.png",               # 417
    "mongols_house_of_wisdom_tigris_ink.png",     # 416
    # ── EP003 Cannae sc16-24 ─────────────────────────────────────────────
    "cannae_legacy_perfect_battle.png",           # 324
    "cannae_reassessment_hannibal.png",           # 323
    "cannae_schlieffen_plan_1914.png",            # 322
    "cannae_why_generals_study_it.png",           # 321
    "cannae_scipio_africanus.png",                # 320
    "cannae_rome_refuses_to_break.png",           # 319
    "cannae_maharbal_reproach.png",               # 318
    "cannae_dead_count_aftermath.png",            # 317
    "cannae_death_of_paullus.png",                # 316
    # ── EP002 Gaugamela sc14-24 (oldest of today's batch) ────────────────
    "gaugamela_modern_plain_legacy.png",          # 224
    "gaugamela_darius_reassessed.png",            # 223
    "gaugamela_military_legacy_west_point.png",   # 222
    "gaugamela_hellenistic_age_library.png",      # 221
    "gaugamela_alexander_persian_court.png",      # 220
    "gaugamela_death_of_darius_bessus.png",       # 219
    "gaugamela_persepolis_burning.png",           # 218
    "gaugamela_babylon_gates_open.png",           # 217
    "gaugamela_aftermath_honors_persian_guard.png", # 216
    "gaugamela_pursuit_darius_escapes.png",       # 215
    "gaugamela_parmenion_crisis_left_flank.png",  # 214
]


def main():
    CHARS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()

    today_pngs = sorted(
        [f for f in DOWNLOADS.glob("*.png")
         if datetime.fromtimestamp(f.stat().st_mtime).date() == today],
        key=lambda f: f.stat().st_mtime,
        reverse=True,   # most recent first
    )

    print(f"Found {len(today_pngs)} PNG files from today in Downloads")
    print(f"Saving to: {CHARS_DIR}\n")

    copied = 0
    for i, src in enumerate(today_pngs):
        if i >= len(BATCH_NAMES):
            name = f"generated_extra_{i:02d}.png"
        else:
            name = BATCH_NAMES[i]

        dest = CHARS_DIR / name
        # Don't overwrite existing files that already have content
        if dest.exists():
            name_stem = dest.stem
            name = f"{name_stem}_dup{i}.png"
            dest = CHARS_DIR / name

        shutil.copy2(str(src), str(dest))
        print(f"  [{i+1:2d}] → character_images/{name}")
        copied += 1

        if i >= 35:   # stop after 36 files
            break

    print(f"\nDone! {copied} images saved to character_images/")
    # Only pause if run directly (not from a batch file)
    import sys
    if sys.stdin.isatty():
        input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
