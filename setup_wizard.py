"""
setup_wizard.py — Empire OS Credential Setup
Run this once. It walks you through every key/password needed,
saves them to .env, and shows you what's set vs missing.

Usage:
    python setup_wizard.py
    python setup_wizard.py --status    # just show what's set/missing, no prompts
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

# All credentials the empire needs
# (key, label, is_password, instructions)
CREDENTIALS = [
    # ── AI ──────────────────────────────────────────────────────────────────
    ("GEMINI_API_KEY",
     "Gemini API Key",
     True,
     "Get it at: https://aistudio.google.com  →  Get API key"),

    # ── YouTube / GG ────────────────────────────────────────────────────────
    ("ELEVENLABS_API_KEY",
     "ElevenLabs API Key (TTS voices)",
     True,
     "Get it at: https://elevenlabs.io  →  Profile  →  API Key"),

    # ── Books ────────────────────────────────────────────────────────────────
    ("KDP_EMAIL",
     "Amazon KDP Email (your Amazon login)",
     False,
     "Same email you use to log into kdp.amazon.com"),

    ("KDP_PASSWORD",
     "Amazon KDP Password",
     True,
     "Your Amazon account password"),

    ("D2D_API_KEY",
     "Draft2Digital API Key (B&N, Apple, Kobo, Scribd...)",
     True,
     "Get it at: https://draft2digital.com  →  Account  →  API"),

    ("PAYHIP_API_KEY",
     "Payhip API Key (your own store)",
     True,
     "Get it at: https://payhip.com  →  Settings  →  API"),

    # ── Merch ───────────────────────────────────────────────────────────────
    ("REDBUBBLE_EMAIL",
     "Redbubble Email",
     False,
     "Your Redbubble artist account email"),

    ("REDBUBBLE_PASSWORD",
     "Redbubble Password",
     True,
     "Your Redbubble password"),

    ("SPRING_EMAIL",
     "Spring (Teespring) Email",
     False,
     "Your Spring/Teespring account email"),

    ("SPRING_PASSWORD",
     "Spring (Teespring) Password",
     True,
     "Your Spring password"),

    ("PRINTFUL_API_KEY",
     "Printful API Key",
     True,
     "Get it at: https://printful.com  →  Settings  →  API"),

    # ── Merch by Amazon ─────────────────────────────────────────────────────
    ("MBA_EMAIL",
     "Merch by Amazon Email (your Amazon login)",
     False,
     "Apply first at: https://merch.amazon.com/landing  (2-8 week wait)\n"
     "  Same email as your Amazon account — enter once approved"),

    ("MBA_PASSWORD",
     "Merch by Amazon Password",
     True,
     "Your Amazon account password (same as KDP if you use same account)"),

    # ── Amazon Associates ────────────────────────────────────────────────────
    ("AMAZON_ASSOCIATES_TAG",
     "Amazon Associates Tracking ID (affiliate tag)",
     False,
     "Apply at: https://affiliate-program.amazon.com\n"
     "  Tag looks like: empireos-20"),

    # ── TikTok Shop ──────────────────────────────────────────────────────────
    ("TIKTOK_SHOP_KEY",
     "TikTok Shop API Key (once seller account approved)",
     True,
     "Apply at: https://seller.tiktokshop.com  →  get API key after approval"),

    # ── Etsy ─────────────────────────────────────────────────────────────────
    ("ETSY_API_KEY",
     "Etsy API Key (for product sync)",
     True,
     "Get it at: https://www.etsy.com/developers/register"),
]

# Deduplicate by key
seen: set[str] = set()
UNIQUE_CREDS: list[tuple] = []
for c in CREDENTIALS:
    if c[0] not in seen:
        seen.add(c[0])
        UNIQUE_CREDS.append(c)


def load_env() -> dict[str, str]:
    """Load existing .env into a dict."""
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def save_env(env: dict[str, str]) -> None:
    """Write dict back to .env, preserving order and adding header."""
    lines = ["# Empire OS — credentials file", "# DO NOT commit this file to git", ""]
    for k, v in env.items():
        lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mask(value: str) -> str:
    """Show first 4 chars then asterisks."""
    if not value:
        return ""
    return value[:4] + "*" * min(len(value) - 4, 12)


def print_status(env: dict[str, str]) -> None:
    print("\n" + "="*60)
    print("  EMPIRE OS — Credential Status")
    print("="*60)
    set_count   = 0
    unset_count = 0
    for key, label, _, _ in UNIQUE_CREDS:
        val = env.get(key, "")
        if val:
            print(f"  [SET]     {label}")
            print(f"            {key} = {mask(val)}")
            set_count += 1
        else:
            print(f"  [MISSING] {label}")
            print(f"            {key}")
            unset_count += 1
    print("="*60)
    print(f"  Set: {set_count}   Missing: {unset_count}")
    print("="*60 + "\n")


def run_wizard(only_missing: bool = True) -> None:
    env = load_env()

    print("\n" + "="*60)
    print("  EMPIRE OS SETUP WIZARD")
    print("  Enter your credentials. Press Enter to skip any.")
    print("  Passwords are hidden as you type.")
    print("="*60 + "\n")

    changed = False
    for key, label, is_password, instructions in UNIQUE_CREDS:
        current = env.get(key, "")

        if only_missing and current:
            continue  # already set, skip

        print(f"  {label}")
        print(f"  {instructions}")
        if current:
            print(f"  Current: {mask(current)}  (press Enter to keep)")

        try:
            if is_password:
                val = getpass.getpass("  > ").strip()
            else:
                val = input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Wizard cancelled. Progress saved.")
            break

        if val:
            env[key] = val
            changed = True
            print(f"  Saved.\n")
        elif current:
            print(f"  Keeping existing value.\n")
        else:
            print(f"  Skipped.\n")

    if changed:
        save_env(env)
        print("  .env updated.\n")

    print_status(env)

    missing = [key for key, _, _, _ in UNIQUE_CREDS if not env.get(key)]
    if missing:
        print(f"  {len(missing)} credential(s) still missing.")
        print("  Re-run  python setup_wizard.py  when you have them.\n")
    else:
        print("  All credentials set. Empire is fully armed.\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--status",      action="store_true", help="Show status only, no prompts")
    p.add_argument("--all",         action="store_true", help="Re-enter all credentials, not just missing ones")
    args = p.parse_args()

    if args.status:
        print_status(load_env())
    else:
        run_wizard(only_missing=not args.all)
