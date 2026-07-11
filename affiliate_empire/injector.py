"""
affiliate_empire/injector.py — Auto-inject affiliate links into content
Adds your affiliate links to:
  - YouTube video descriptions
  - Book back-matter (end of each StoryForge book)
  - Store widget HTML
  - Newsletter templates

Usage:
    python affiliate_empire/injector.py --type description --channel gg
    python affiliate_empire/injector.py --type book
    python affiliate_empire/injector.py --all
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

STATUS_FILE = Path(__file__).parent / "AFFILIATE_STATUS.json"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def build_description_footer(channel: str = "gg") -> str:
    """Build the affiliate links section for YouTube descriptions."""
    env = load_env()

    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🔗 TOOLS & RESOURCES I USE:",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # ElevenLabs — fits all channels
    el_id = env.get("ELEVENLABS_AFFILIATE_ID", "")
    if el_id:
        lines.append(f"🎙️ AI Voice (ElevenLabs) → https://elevenlabs.io/?via={el_id}")

    # TubeBuddy
    tb_id = env.get("TUBEBUDDY_AFFILIATE_ID", "")
    if tb_id:
        lines.append(f"📈 Grow Your Channel (TubeBuddy) → https://www.tubebuddy.com/pricing?a={tb_id}")

    # VidIQ
    vi_id = env.get("VIDIQ_AFFILIATE_ID", "")
    if vi_id:
        lines.append(f"📊 YouTube Analytics (VidIQ) → https://vidiq.com/?ref={vi_id}")

    # NordVPN — fits all channels
    nord_id = env.get("NORDVPN_AFFILIATE_ID", "")
    if nord_id:
        lines.append(f"🔒 Stay Private Online (NordVPN) → https://nordvpn.com/?utm_medium=affiliate&utm_term={nord_id}")

    # Canva
    canva_id = env.get("CANVA_AFFILIATE_ID", "")
    if canva_id:
        lines.append(f"🎨 Design Tool (Canva) → https://www.canva.com/join/{canva_id}")

    # Channel-specific
    if channel in ("gg", "lo"):
        mc_id = env.get("MASTERCLASS_AFFILIATE_ID", "")
        if mc_id:
            lines.append(f"🎓 Learn From the Best (MasterClass) → https://www.masterclass.com/?clickId={mc_id}")

    if channel == "ed":
        sk_id = env.get("SKILLSHARE_AFFILIATE_ID", "")
        if sk_id:
            lines.append(f"💻 Learn AI & Tech (Skillshare) → https://skillshare.eevideo.net/c/{sk_id}")

    # Patreon
    patreon = env.get("PATREON_URL", "")
    if patreon:
        channel_names = {"gg": "Gods & Glory", "il": "Iron Legends", "lo": "Little Olympus", "ed": "Empire Decoded"}
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"❤️ SUPPORT {channel_names.get(channel, 'US').upper()} ON PATREON:",
            f"→ {patreon}",
            "Get early episodes, behind-the-scenes, and more!",
        ]

    # Store
    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "👕 OFFICIAL MERCH:",
        "→ https://www.redbubble.com/people/EmpireDesigns/shop",
    ]

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def build_book_backmatter() -> str:
    """Build affiliate links section for end of StoryForge books."""
    env = load_env()
    amazon_tag = env.get("AMAZON_ASSOCIATES_TAG", "")
    audible_tag = env.get("AUDIBLE_AFFILIATE_TAG", "")
    patreon = env.get("PATREON_URL", "")
    gumroad = env.get("GUMROAD_URL", "")

    lines = [
        "",
        "─" * 50,
        "ENJOYED THIS BOOK? HERE'S WHAT TO DO NEXT",
        "─" * 50,
        "",
        "📚 FIND MORE BOOKS LIKE THIS:",
    ]

    if amazon_tag:
        lines.append(f"  Amazon → https://www.amazon.com/s?k=empire+designs&tag={amazon_tag}")

    if audible_tag:
        lines.append(f"  Audiobook on Audible → https://www.audible.com/search?keywords=empire+designs")

    lines += [
        "",
        "🎥 WATCH THE YOUTUBE CHANNEL:",
        "  Gods & Glory → https://youtube.com/@GodsAndGloryAI",
        "  Empire Decoded → https://youtube.com/@EmpireDecodedAI",
        "",
    ]

    if patreon:
        lines += [
            "❤️ SUPPORT US ON PATREON:",
            f"  {patreon}",
            "  Get exclusive content and early access to new books!",
            "",
        ]

    if gumroad:
        lines += [
            "⚡ FREE RESOURCES & PROMPT PACKS:",
            f"  {gumroad}",
            "",
        ]

    lines += [
        "📧 JOIN THE NEWSLETTER:",
        "  Get notified of new releases and exclusive deals.",
        "  → [Your newsletter URL here]",
        "",
        "─" * 50,
        "Thank you for reading. Leave a review — it helps more",
        "people discover this book and keeps the series going!",
        "─" * 50,
    ]

    return "\n".join(lines)


def inject_into_descriptions(channel: str = "gg") -> None:
    """Print a ready-to-paste description footer for the given channel."""
    footer = build_description_footer(channel)
    out_file = ROOT / "affiliate_empire" / f"description_footer_{channel}.txt"
    out_file.write_text(footer, encoding="utf-8")
    print(f"\n  ✓ Description footer saved: {out_file}")
    print(f"\n  PASTE THIS INTO ALL {channel.upper()} VIDEO DESCRIPTIONS:")
    print(footer)


def inject_into_books() -> None:
    """Save book back-matter to a file StoryForge can append."""
    backmatter = build_book_backmatter()
    out_file   = ROOT / "affiliate_empire" / "book_backmatter.txt"
    out_file.write_text(backmatter, encoding="utf-8")
    print(f"\n  ✓ Book back-matter saved: {out_file}")
    print(f"    StoryForge formatter will auto-append this to every book.")
    print(backmatter)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Affiliate Link Injector")
    ap.add_argument("--type",    choices=["description", "book", "all"], default="all")
    ap.add_argument("--channel", default="gg", choices=["gg", "il", "lo", "ed"])
    args = ap.parse_args()

    if args.type in ("description", "all"):
        channels = ["gg", "il", "lo", "ed"] if args.type == "all" else [args.channel]
        for ch in channels:
            inject_into_descriptions(ch)

    if args.type in ("book", "all"):
        inject_into_books()
