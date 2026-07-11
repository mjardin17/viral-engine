"""
merch_empire/platform_tracker.py — Empire OS Platform Application Tracker
Tracks which platforms Josh has applied to, approval status, and next steps.

Platforms that require applications / approval:
  - Merch by Amazon (MBA)  — invite/waitlist at merch.amazon.com
  - TikTok Shop            — business account + shop application
  - Etsy Seller            — just an account, no approval needed
  - Amazon Associates      — affiliate program for website links

Usage:
    python merch_empire/platform_tracker.py --status
    python merch_empire/platform_tracker.py --apply mba
    python merch_empire/platform_tracker.py --apply tiktok-shop
    python merch_empire/platform_tracker.py --mark-approved mba
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

TRACKER_FILE = Path(__file__).parent / "PLATFORM_STATUS.json"

# ── Platform definitions ──────────────────────────────────────────────────────

PLATFORMS = {
    "mba": {
        "name":         "Merch by Amazon",
        "apply_url":    "https://merch.amazon.com/landing",
        "type":         "waitlist",
        "avg_wait":     "2–8 weeks",
        "requirements": [
            "Amazon seller or buyer account",
            "US address preferred (or use business address)",
            "Describe your design experience + intended use",
            "Be honest: say you create AI-generated art for multiple niches",
        ],
        "once_approved": [
            "Start with Tier 10 (10 designs max)",
            "Upload 10 designs, wait for 10 sales to tier up to Tier 25",
            "Royalty: ~$2–$7 per shirt depending on price point",
            "Best price: $19.99 for volume, $24.99 for margin",
        ],
        "uploader": "merch_empire/amazon.py",
    },
    "tiktok-shop": {
        "name":         "TikTok Shop (Seller)",
        "apply_url":    "https://seller.tiktokshop.com/",
        "type":         "application",
        "avg_wait":     "1–5 business days",
        "requirements": [
            "TikTok Business Account (set up first via SOCIAL_SETUP.bat)",
            "Government-issued ID or EIN / business registration",
            "US bank account for payouts",
            "Your TikTok account must be in good standing",
        ],
        "once_approved": [
            "List merch products with product images from merch_empire/designer.py",
            "TikTok Shop charges 2–8% commission per sale",
            "Link your Printful products for fulfillment",
            "Videos can tag products directly → massive conversion potential",
        ],
        "uploader": None,  # manual for now — API coming
    },
    "etsy": {
        "name":         "Etsy Seller",
        "apply_url":    "https://www.etsy.com/sell",
        "type":         "instant",
        "avg_wait":     "instant",
        "requirements": [
            "Etsy account (create at etsy.com)",
            "Credit card for setup fees (~$0.20/listing)",
            "PayPal or bank account for payouts",
        ],
        "once_approved": [
            "Use Printful x Etsy integration for print-on-demand fulfillment",
            "Create listing → Printful auto-fulfills orders",
            "Etsy SEO: use exact niche keywords in title and tags",
        ],
        "uploader": None,  # Printful <-> Etsy integration handles it
    },
    "amazon-associates": {
        "name":         "Amazon Associates (Affiliate)",
        "apply_url":    "https://affiliate-program.amazon.com/",
        "type":         "application",
        "avg_wait":     "1–3 days (auto-approved, then reviewed after first 3 sales)",
        "requirements": [
            "Website URL (your store/channel site)",
            "Describe how you'll promote Amazon products",
            "Must make 3 qualifying sales in first 180 days or account closes",
        ],
        "once_approved": [
            "Generate affiliate links for your MBA products",
            "Add to website store → earn 4–10% on top of royalties",
            "Also works for book links (Kindle / paperback)",
        ],
        "uploader": None,
    },
}


# ── Status helpers ────────────────────────────────────────────────────────────

def load_status() -> dict:
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
    return {}


def save_status(data: dict) -> None:
    TRACKER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def set_applied(key: str) -> None:
    data = load_status()
    if key not in data:
        data[key] = {}
    data[key]["applied"]      = True
    data[key]["applied_date"] = datetime.now().strftime("%Y-%m-%d")
    data[key]["approved"]     = data[key].get("approved", False)
    save_status(data)
    print(f"\n  ✓ Marked {PLATFORMS[key]['name']} as APPLIED — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Now waiting for approval (avg: {PLATFORMS[key]['avg_wait']})")


def set_approved(key: str) -> None:
    data = load_status()
    if key not in data:
        data[key] = {}
    data[key]["approved"]      = True
    data[key]["approved_date"] = datetime.now().strftime("%Y-%m-%d")
    save_status(data)
    print(f"\n  🎉 {PLATFORMS[key]['name']} APPROVED!")
    p = PLATFORMS[key]
    if p.get("once_approved"):
        print("\n  NEXT STEPS:")
        for step in p["once_approved"]:
            print(f"    → {step}")


def open_url(url: str) -> None:
    try:
        subprocess.Popen(["cmd", "/c", "start", url], shell=False)
    except Exception:
        print(f"    Open manually: {url}")


# ── Status display ────────────────────────────────────────────────────────────

def print_status() -> None:
    data = load_status()
    print("\n" + "=" * 60)
    print("  EMPIRE OS — Platform Application Status")
    print("=" * 60)

    for key, p in PLATFORMS.items():
        state     = data.get(key, {})
        applied   = state.get("applied",  False)
        approved  = state.get("approved", False)
        app_date  = state.get("applied_date",  "")
        appr_date = state.get("approved_date", "")

        if approved:
            icon = "✅"
            status = f"APPROVED {appr_date}"
        elif applied:
            icon = "⏳"
            status = f"APPLIED {app_date} — waiting (avg {p['avg_wait']})"
        else:
            icon = "❌"
            status = f"Not applied — run: python merch_empire/platform_tracker.py --apply {key}"

        print(f"\n  {icon}  {p['name']}")
        print(f"       {status}")
        if not applied:
            print(f"       Apply at: {p['apply_url']}")

    print("\n" + "=" * 60)


# ── Application guide ─────────────────────────────────────────────────────────

def print_apply_guide(key: str) -> None:
    p = PLATFORMS[key]
    print(f"\n{'=' * 60}")
    print(f"  APPLYING TO: {p['name']}")
    print(f"  Type   : {p['type']} ({p['avg_wait']})")
    print(f"{'=' * 60}")

    print("\n  REQUIREMENTS:")
    for req in p["requirements"]:
        print(f"    • {req}")

    if p.get("once_approved"):
        print("\n  ONCE APPROVED YOU CAN:")
        for step in p["once_approved"]:
            print(f"    → {step}")

    print(f"\n  Opening application page...")
    open_url(p["apply_url"])

    input("\n  [Press Enter when you've submitted the application] > ")
    set_applied(key)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Platform Application Tracker")
    ap.add_argument("--status",        action="store_true")
    ap.add_argument("--apply",         metavar="PLATFORM")
    ap.add_argument("--mark-approved", metavar="PLATFORM")
    ap.add_argument("--list",          action="store_true")
    args = ap.parse_args()

    if args.status or not any([args.apply, args.mark_approved, args.list]):
        print_status()

    if args.list:
        print("\n  Available platforms:")
        for k in PLATFORMS:
            print(f"    {k}")

    if args.apply:
        k = args.apply.lower()
        if k not in PLATFORMS:
            print(f"  Unknown platform '{k}'. Options: {', '.join(PLATFORMS)}")
        else:
            print_apply_guide(k)

    if args.mark_approved:
        k = args.mark_approved.lower()
        if k not in PLATFORMS:
            print(f"  Unknown platform '{k}'. Options: {', '.join(PLATFORMS)}")
        else:
            set_approved(k)
